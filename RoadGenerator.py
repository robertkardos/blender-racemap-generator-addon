import bpy, bmesh
import math, mathutils
import numpy as np
import random
import copy
from triangle import *

from bpy.props import (StringProperty, PointerProperty)
from bpy.types import (Panel, PropertyGroup)

finalCollection = "Terrain"

class MySettings(bpy.types.PropertyGroup):
    landscape : StringProperty(
        name="Base terrain",
        description=":",
        default="Landscape",
        maxlen=1024
    )

def createCircularIterator(roads):
    iterRoads = iter(roads)
    returnRoads = [next(iterRoads)]

    for road in iterRoads:
        returnRoads.append(road)
        yield returnRoads
        returnRoads.pop(0)

    returnRoads.append(roads[0])
    yield returnRoads

def tupleCircularShift(tuple):
    for (a0,a1),(b0,b1) in zip(tuple[1:], tuple):
        yield(a0,b1)
    yield(tuple[0][0], tuple[-1][1])

def angle_between(v1, v2):
    p1 = (v1.x, v1.y)
    p2 = (v2.x, v2.y)
    
    ang1 = np.arctan2(*p1[::-1])
    ang2 = np.arctan2(*p2[::-1])
    return np.rad2deg((ang1 - ang2) % (2 * np.pi))

class RoadElement():
    object: bpy.types.Object
    metadata: {}
    def __init__(self, object, metadata):
        self.object = object
        self.metadata = metadata


class HelloWorldPanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Race map generator"
    bl_idname = "OBJECT_PT_helloasdasd"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    def draw(self, context):
        layout = self.layout
        obj = context.object
        myPropertiesasd = context.scene.myPropertiesasd
#        row = layout.row()
#        worth_group_tools = context.scene.worth_group_tools
#        print(worth_group_tools)
#        row.prop(worth_group_tools, "name")
        row = layout.row()
        row.prop(myPropertiesasd, "landscape")
        
        
        row = layout.row()
        row.operator("mesh.primitive_uv_sphere_add", text="Add intersection")
        row = layout.row()
        row.operator("wm.hello_world", text="Run road baking")
        row = layout.row()
        row.operator("wm.export_prep", text="Pre-export")


class RunRoadBaking(bpy.types.Operator):
    bl_idname = "wm.hello_world"
    bl_label = "Minimal Operator"
    roadSegment: bpy.types.Object
    
    def execute(self, context):
        print("-------- GENERATE --------")
        RunRoadBaking.cleanUpCreatedRoads()
        RunRoadBaking.cleanUpCreatedShaite()
        
        scene = bpy.context.scene
        RANGE_OF_INTERSECTION = 10
        
        for curve in bpy.data.collections["Curves"].objects:
            RunRoadBaking.setUpRoadSegment(self)
            RunRoadBaking.setUpRoadModifiersAndConstraint(self, curve)
        
        bpy.ops.object.select_all(action='DESELECT')
        
        for intersection in bpy.data.collections["Intersections"].objects:
            intersection.select_set(True)
            bpy.context.view_layer.objects.active = intersection
#            bpy.context.view_layer.objects.road = intersection
            roadsCloseToIntersection = []
            me = intersection.data
            roadObjects = [o for o in bpy.data.collections["Roads"].objects]
            bm = bmesh.new()
            for road in roadObjects:
                smwi = road.matrix_world.inverted()
                bm.from_mesh(me)
                bm.verts.ensure_lookup_table()
                vert = bm.verts[0]
                v1 = intersection.matrix_world @ vert.co # global face median
                local_pos = smwi @ v1  # face cent in sphere local space
                (hit, loc, norm, face_index) = road.closest_point_on_mesh(local_pos)
                if hit:
                    v2 = road.matrix_world @ loc
                    distance = (v2 - v1).length
                    
                    if distance < RANGE_OF_INTERSECTION:
                        roadsCloseToIntersection.append(road)
                bm.clear()
            
            if len(roadsCloseToIntersection) > 0:
                roadsWithMetadata = RunRoadBaking.pairRoadsToTheirIntersectionPoints(roadsCloseToIntersection, intersection)
                orderedRoads = RunRoadBaking.orderRoadsAroundIntersectionCCW(roadsWithMetadata, intersection)
                RunRoadBaking.connectRoadsInIntersection(orderedRoads, intersection)
        
        roadNetwork = RunRoadBaking.joinRoadsAndIntersections()
        terrainFragments = RunRoadBaking.createTerrainFragments(roadNetwork)
        roadNetwork.select_set(False)
        
        print('Terrain fragments: ', len(terrainFragments))
        for terrainFragment in terrainFragments:
            bpy.data.collections['Terrain'].objects.link(terrainFragment)
            RunRoadBaking.shrinkwrapTerrain(terrainFragment)
            terrainFragment.select_set(True)
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
#            bpy.ops.mesh.fill()
            bpy.ops.mesh.edge_face_add()
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            terrainFragment.select_set(False)
#            terrainFragment.select_set(True)
        
        
        for obj in bpy.data.collections['Terrain'].all_objects:
            obj.select_set(True)
        for obj in bpy.data.collections['Shaite'].all_objects:
            obj.select_set(True)
        
        bpy.ops.object.join()
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type="VERT")
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.remove_doubles()
        bpy.ops.object.mode_set(mode='OBJECT')
        
        
        roadsAndTerrain = bpy.context.object
        
        roadsAndTerrain.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
#        bpy.ops.object.mode_set(mode='OBJECT')
        terrainGroup = roadsAndTerrain.vertex_groups["Terrain"]
        roadsAndTerrain.vertex_groups.active = terrainGroup
        bpy.ops.object.vertex_group_select()
#        roadsAndTerrain.active_material_index = roadsAndTerrain.material_slots.keys().index('Grass')
        bpy.ops.object.material_slot_add()
        bpy.context.object.active_material = bpy.data.materials['Grass']
        bpy.ops.object.material_slot_assign()

        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')

        roadsAndTerrain.name = "Map"
#        roadsAndTerrain.collections.link

        print("-------- DONE --------")
        return {'FINISHED'}
    
    
    @staticmethod
    def shrinkwrapTerrain(terrain):
        terrain.select_set(True, view_layer=bpy.context.view_layer)
        bpy.context.view_layer.objects.active = terrain
        bpy.ops.object.modifier_add(type='SHRINKWRAP')
        terrain.modifiers['Shrinkwrap'].target = bpy.data.objects['Landscape']
        terrain.modifiers["Shrinkwrap"].vertex_group = "Terrain"
        terrain.modifiers["Shrinkwrap"].wrap_method = 'PROJECT'
        terrain.modifiers["Shrinkwrap"].use_project_z = True
        terrain.modifiers["Shrinkwrap"].use_negative_direction = True
        terrain.modifiers["Shrinkwrap"].use_positive_direction = True

        bpy.ops.object.modifier_apply(apply_as='DATA', modifier='Shrinkwrap')

#        self.roadSegment.modifiers['Array'].curve = curve
#        self.roadSegment.modifiers['Array'].use_merge_vertices = True

#        bpy.ops.object.modifier_add(type='CURVE')
#        self.roadSegment.modifiers['Curve'].object = curve
#        bpy.ops.object.constraint_add(type='COPY_LOCATION')
#        
#        self.roadSegment.constraints["Copy Location"].target = curve

#        bpy.ops.object.modifier_apply(apply_as='DATA', modifier='Array')
#        bpy.ops.object.modifier_apply(apply_as='DATA', modifier='Curve')
    
    
    @staticmethod
    def connectRoadsInIntersection(roads, intersection): # fuck this specifically
        roadPairGenerator = createCircularIterator(roads)

        AAAsegments = []
        AAAinnerCurveEndpoints = []
        
        for roadPair in roadPairGenerator:
            roadSegmentLayers = []
            roadSegmentBMesh = bmesh.new()
            AAAcurvesBM = []
            AAAcurves = []
            numOfLayers = 3
            
            for layer in range(numOfLayers):
                p1 = roadPair[0].metadata["Left_" + str(layer)][0]
                p2 = roadPair[1].metadata["Right_" + str(layer)][0]
                h1 = roadPair[0].metadata["Left_" + str(layer)][1]
                h2 = roadPair[1].metadata["Right_" + str(layer)][1]

                layerCurveSegmentObject = RunRoadBaking.createLayerCurveSegment(intersection.location, p1, p2, h1, h2)
                
                curve = layerCurveSegmentObject
                curve.vertex_groups.new(name="Curve_" + str(layer))
                curve.vertex_groups["Curve_" + str(layer)].add(list(map(lambda v: v.index, curve.data.vertices)), 1.0, 'ADD')
                
                AAAcurves.append(curve)
                
                curveBM = bmesh.new()
                curveBM.from_mesh(curve.data)
                AAAcurvesBM.append(curveBM)
            
            firstVertex = curve.data.vertices[0]
            lastVertex = curve.data.vertices[-1]
            AAAinnerCurveEndpoints.append((copy.deepcopy(firstVertex.co), copy.deepcopy(lastVertex.co)))
            roadSegmentObjectBM = bmesh.new()

            # BRIDGE BETWEEN PAIRS OF CURVES
            bpy.ops.object.select_all(action='DESELECT')
            for curve in AAAcurves:
                curve.select_set(True)
            bpy.ops.object.join()
            
            for i in range(numOfLayers - 1):
                bpy.ops.object.mode_set(mode = 'EDIT')
                bpy.ops.mesh.select_all(action = 'DESELECT')
                
                caGroup = bpy.context.object.vertex_groups['Curve_' + str(i)]
                cbGroup = bpy.context.object.vertex_groups['Curve_' + str(i + 1)]
                
                bpy.context.object.vertex_groups.active = caGroup
                bpy.ops.object.vertex_group_select()
                bpy.context.object.vertex_groups.active = cbGroup
                bpy.ops.object.vertex_group_select()
                
                bpy.ops.mesh.looptools_bridge(cubic_strength=1, interpolation='cubic', loft=False, loft_loop=False, min_width=0, mode='shortest', remove_faces=True, reverse=False, segments=1, twist=0)
                bpy.ops.object.mode_set(mode='OBJECT')
            # / BRIDGE BETWEEN PAIRS OF CURVES
            
            AAAsegments.append(bpy.context.object)
        
        for segment in AAAsegments:
            segment.select_set(True)
        bpy.ops.object.join()
        
        
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        
        # CONNECT INNERMOST POINTS ALONG ROADS
        innerCurveEndpointsGenerator = tupleCircularShift(AAAinnerCurveEndpoints)
        for pointPair in innerCurveEndpointsGenerator:
            for v in bpy.context.object.data.vertices:
                if v.co == pointPair[0]:
                    vert1 = v.index
            for v in bpy.context.object.data.vertices:
                if v.co == pointPair[1]:
                    vert2 = v.index
            bpy.context.object.data.edges.add(1)
            edgeIndex = len(bpy.context.object.data.edges) - 1
            bpy.context.object.data.edges[edgeIndex].vertices[0] = vert1
            bpy.context.object.data.edges[edgeIndex].vertices[1] = vert2
        intersectionObj = bpy.context.object
        # / CONNECT INNERMOST POINTS ALONG ROADS
        
        # FILL INSIDE OF INTERSECTION
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action = 'DESELECT')
        innermostCurveGroup = bpy.context.object.vertex_groups['Curve_' + str(numOfLayers - 1)]
        bpy.context.object.vertex_groups.active = innermostCurveGroup
        bpy.ops.object.vertex_group_select()
        bpy.ops.mesh.fill()
        bpy.ops.object.mode_set(mode = 'OBJECT')
        # / FILL INSIDE OF INTERSECTION

        
    @staticmethod
    def createLayerCurveSegment(location, p1, p2, h1, h2):
        bpy.ops.curve.primitive_bezier_curve_add(enter_editmode=False, align='WORLD', location=location)
        curve = bpy.context.object
        
        
        minDistance = math.dist(p1, p2)
        
        curve.data.splines[0].bezier_points[0].handle_left = h1 - curve.location
        curve.data.splines[0].bezier_points[0].co = p1 - curve.location
        curve.data.splines[0].bezier_points[1].co = p2 - curve.location
        curve.data.splines[0].bezier_points[1].handle_right = h2 - curve.location
        
        vecOutwards1 = (p1 - h1)
        vecOutwards1.normalize()
        vecOutwards2 = (p2 - h2)
        vecOutwards2.normalize()
        vecOutwards1.magnitude = vecOutwards1.magnitude * minDistance / 2
        vecOutwards2.magnitude = vecOutwards2.magnitude * minDistance / 2
        
        curve.data.splines[0].bezier_points[0].handle_right = p1 - curve.location + vecOutwards1
        curve.data.splines[0].bezier_points[1].handle_left = p2 - curve.location + vecOutwards2
        
#            bpy.ops.object.convert(target="MESH")
#            roadSideBMesh = bmesh.new()
#            roadSideBMesh.from_mesh(curve.data)
#            roadSideBMesh.verts.ensure_lookup_table()
#            firstVertex = roadSideBMesh.verts[0]
#            lastVertex = roadSideBMesh.verts[-1]
#            
#            roadSidesBMesh.append(roadSideBMesh)
        
        bpy.context.view_layer.objects.active = curve
        curve.select_set(True)
        
        bpy.ops.object.convert(target="MESH")
        
        return curve
    
    
    @staticmethod
    def pairRoadsToTheirIntersectionPoints(roads, intersection):
        roadsWithMetadata = []
        
        for road in roads:
            setsOfClosestPoints = RunRoadBaking.getClosestPointsToIntersection(road, intersection)
#            RunRoadBaking.drawLine(setsOfClosestPoints
            roadElement = RoadElement(road, setsOfClosestPoints)
            roadsWithMetadata.append(roadElement)
            
        return roadsWithMetadata
    
    
    @staticmethod
    def getClosestPointsToIntersection(road, intersection):
        pairsOfClosestPoints = {}
        centerVertices = [vert for vert in road.data.vertices if road.vertex_groups['Center'].index in [i.group for i in vert.groups]]
        
        for i in range(math.floor(len(road.vertex_groups)/2)): # for every layer:
            leftVertices  = [vert for vert in road.data.vertices if road.vertex_groups["Left_" + str(i)].index in [i.group for i in vert.groups]]
            rightVertices = [vert for vert in road.data.vertices if road.vertex_groups["Right_" + str(i)].index in [i.group for i in vert.groups]]
            mappedCenterVertices = list(map(lambda vertex: road.matrix_world @ vertex.co, centerVertices))
            mappedLeftVertices  = list(map(lambda vertex: road.matrix_world @ vertex.co, leftVertices))
            mappedRightVertices = list(map(lambda vertex: road.matrix_world @ vertex.co, rightVertices))
             
            pairsOfClosestPoints["Center"] = RunRoadBaking.closestPointPairInVertexGroup(mappedCenterVertices, intersection)
            pairA = RunRoadBaking.closestPointPairInVertexGroup(mappedLeftVertices, intersection)
            pairB = RunRoadBaking.closestPointPairInVertexGroup(mappedRightVertices, intersection)
            
            p1 = intersection.location.xy
            p2 = pairA[0].xy
            p3 = pairB[0].xy
            angle = angle_between(p3 - p1, p2 - p1)
#            breakpoint()
            if angle > 180: # the left side is actually more to the left
                pairsOfClosestPoints["Left_" + str(i)]  = pairA
                pairsOfClosestPoints["Right_" + str(i)] = pairB
            else:
                pairsOfClosestPoints["Left_" + str(i)]  = pairB
                pairsOfClosestPoints["Right_" + str(i)] = pairA
        
        return pairsOfClosestPoints
    
    
    @staticmethod
    def closestPointPairInVertexGroup(mappedVertices, intersection):
        dist1 = math.dist(intersection.location, mappedVertices[0])
        dist2 = math.dist(intersection.location, mappedVertices[-1])
        if dist1 < dist2:
            points = (mappedVertices[0], mappedVertices[1])
        else:
            points = (mappedVertices[-1], mappedVertices[-2])
        return points
    
    
    @staticmethod
    def orderRoadsAroundIntersectionCCW(roads, intersection):
        roadsOrderedByAngles = []
        orderedMapped = []
        p1 = intersection.location.xy
        p2 = mathutils.Vector((intersection.location.x, intersection.location.y + 20))
        for road in roads:
            p3 = road.metadata["Center"][0].xy
            angle = angle_between(p3 - p1, p2 - p1) # angle = numpy.arccos((math.dist(p1, p2)**2 + math.dist(p1, p3)**2 - math.dist(p2, p3)**2) / (2 * math.dist(p1, p2) * math.dist(p1, p3)))
            roadsOrderedByAngles.append((road, angle))
        roadsOrderedByAngles.sort(key = lambda road: road[1])
        for road in roadsOrderedByAngles:
            orderedMapped.append(road[0])
        return orderedMapped
    
    
    @staticmethod
    def setUpRoadModifiersAndConstraint(self, curve):
        bpy.context.view_layer.objects.active = self.roadSegment
        bpy.ops.object.modifier_add(type="ARRAY")
        self.roadSegment.modifiers["Array"].fit_type = "FIT_CURVE"
        self.roadSegment.modifiers["Array"].curve = curve
        self.roadSegment.modifiers["Array"].use_merge_vertices = True

        bpy.ops.object.modifier_add(type='CURVE')
        self.roadSegment.modifiers["Curve"].object = curve
        bpy.ops.object.constraint_add(type='COPY_LOCATION')
        
        self.roadSegment.constraints["Copy Location"].target = curve

        bpy.ops.object.modifier_apply(apply_as='DATA', modifier="Array")
        bpy.ops.object.modifier_apply(apply_as='DATA', modifier="Curve")

    @staticmethod
    def setUpRoadSegment(self):
        roadSegmentORIGINAL = bpy.data.objects["DefaultAsphalt_3Segment"]
        roadSegmentORIGINAL.select_set(True)
        self.roadSegment = roadSegmentORIGINAL.copy()
        self.roadSegment.data = roadSegmentORIGINAL.data.copy()

        self.roadSegment.name = "road_segment_TMP"
        self.roadSegment.data.name = "road_segment_data_TMP"
        bpy.data.collections["Roads"].objects.link(self.roadSegment)

    @staticmethod
    def cleanUpCreatedRoads():
        bpy.ops.object.select_all(action='DESELECT')
        for o in bpy.data.collections["Roads"].objects:
            o.select_set(True)
            
        bpy.ops.object.delete(use_global=False, confirm=False)
    
    @staticmethod
    def cleanUpCreatedShaite():
        bpy.ops.object.select_all(action='DESELECT')
        for o in bpy.data.collections["Shaite"].objects:
            o.select_set(True)
            
        bpy.ops.object.delete(use_global=False, confirm=False)
    
    @staticmethod
    def drawLine(p1, p2):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=p1)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=p2)
    
    @staticmethod
    def distanceOfObjects(intersection, object):
        closestPoint = object.closest_point_on_mesh(intersection.location)[1]
        distance = math.dist(closestPoint, intersection.location)
        return distance

    @staticmethod
    def joinRoadsAndIntersections():
        for obj in bpy.data.collections['Roads'].all_objects:
            obj.select_set(True)
        for obj in bpy.data.collections['Shaite'].all_objects:
            obj.select_set(True)
        
        bpy.ops.object.join()
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles()
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        return bpy.context.object
    
    
    @staticmethod
    def createTerrainFragments(roadNetworkObj):
        terrainFragments = []
        
        ROADOBJ = roadNetworkObj
        
        location = ROADOBJ.location
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles()
        
        # select all side edges
        bpy.ops.mesh.select_all( action = 'DESELECT' )
        
        cGroup = ROADOBJ.vertex_groups['Curve_0']
        lGroup = ROADOBJ.vertex_groups['Left_0']
        rGroup = ROADOBJ.vertex_groups['Right_0']
        ROADOBJ.vertex_groups.active = cGroup
        bpy.ops.object.vertex_group_select()
        ROADOBJ.vertex_groups.active = lGroup
        bpy.ops.object.vertex_group_select()
        ROADOBJ.vertex_groups.active = rGroup
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.mode_set(mode = 'OBJECT')
        # / select all side edges
        
        selected_verts = [v for v in ROADOBJ.data.vertices if v.select]
        ROADOBJ.vertex_groups.new(name='Edge')
        ROADOBJ.vertex_groups['Edge'].add(list(map(lambda v: v.index, selected_verts)), 1.0, 'ADD')
        
        
        i = 0
        while (len(selected_verts) > 0):
            bpy.ops.object.mode_set(mode = 'EDIT')
            bpy.ops.mesh.select_all(action = 'DESELECT')
            bpy.ops.object.mode_set(mode = 'OBJECT')
            print('SELECTION: ', i)
            
            # SELECT A VERTEX FROM VERTEX_GROUP['Edge']
            indexOfEdgeVertexGroup = ROADOBJ.vertex_groups['Edge'].index
            vertexPairOnEdge = []
            for v in ROADOBJ.data.vertices:
                for group in v.groups:
                    if group.group == indexOfEdgeVertexGroup:
                        vertexPairOnEdge.append(v)
#                        print('FOUND VERTEX ON EDGE')
                        break
                if len(vertexPairOnEdge) > 1:
#                    print('Found EDGE')
                    break
            
            vertexPairOnEdge[0].select = True
            vertexPairOnEdge[1].select = True
            bpy.ops.object.mode_set(mode = 'EDIT')
            bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
            bpy.ops.mesh.loop_multi_select(ring=False)
            bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT')
            bpy.ops.object.mode_set(mode = 'OBJECT')
            selected_verts = [v for v in ROADOBJ.data.vertices if v.select]
            selected_edges = [e for e in ROADOBJ.data.edges if e.select]
            
            bm = bmesh.new()
            bm.from_mesh(ROADOBJ.data)
            new_mesh = bmesh.new()
            onm = {} # old index to new vert map
            
            for v in [v for v in bm.verts if v.select]:
                nv = new_mesh.verts.new(v.co)
                onm[v.index] = nv
            
            new_mesh.verts.index_update()
            for e in [e for e in bm.edges if e.select]:
                nfverts = [onm[v.index] for v in e.verts]
                new_mesh.edges.new(nfverts)
            
            ROADOBJ.vertex_groups['Edge'].remove(list(map(lambda v: v.index, selected_verts)))
            
            if i == 0: # the outer loop
                corner1 = list((bpy.data.objects['MARKER_Corner_X-Y-'].location - ROADOBJ.location).xy)
                corner2 = list((bpy.data.objects['MARKER_Corner_X+Y-'].location - ROADOBJ.location).xy)
                corner3 = list((bpy.data.objects['MARKER_Corner_X+Y+'].location - ROADOBJ.location).xy)
                corner4 = list((bpy.data.objects['MARKER_Corner_X-Y+'].location - ROADOBJ.location).xy)
                corners = [corner1, corner2, corner3, corner4]
                hole = list((bpy.data.objects['MARKER_Inside'].location - ROADOBJ.location).xy)
                borderBM = bmesh.new()

                for corner in corners:
                    borderBM.verts.new((corner[0], corner[1], 0))
                borderBM.verts.ensure_lookup_table()
                borderBM.edges.new((borderBM.verts[0], borderBM.verts[1]))
                borderBM.edges.new((borderBM.verts[1], borderBM.verts[2]))
                borderBM.edges.new((borderBM.verts[2], borderBM.verts[3]))
                borderBM.edges.new((borderBM.verts[3], borderBM.verts[0]))
                
                borderBM.verts.index_update()
                
                tmpMesh = bpy.data.meshes.new("tmpMesh")
                borderBM.to_mesh(tmpMesh)
                new_mesh.from_mesh(tmpMesh)
                triangulizedSurface = RunRoadBaking.triangulizeAround(new_mesh, corners, hole)
                triangulizedSurface.location = location
                terrainFragments.append(triangulizedSurface)
            else:
#                RunRoadBaking.triangulize(selected_verts, selected_edges)
                triangulizedSurface = RunRoadBaking.triangulize(new_mesh)
                triangulizedSurface.location = location
                terrainFragments.append(triangulizedSurface)
            
            i += 1
            
            selected_verts = [v for v in ROADOBJ.data.vertices if indexOfEdgeVertexGroup in [i.group for i in v.groups]]
            print('NEXT round SELECTED verts: ', len(selected_verts))
    
        return terrainFragments
    
        
    @staticmethod
    def triangulizeAround(terrainBM, corners, hole):
        terrainBM.verts.index_update()
        mappedVerts = list(map(lambda v: list(v.co.xy), list(terrainBM.verts)))
        v = mappedVerts
        numOfBoundaryVertices = len(mappedVerts) - 4
        s = list(map(lambda e: [e.verts[0].index, e.verts[1].index], list(terrainBM.edges)))
        t = triangulate({'vertices': v, 'holes': [hole], 'segments': s}, 'qpa14.1')
        newVertices = t['vertices'].tolist()
        for i in range(len(mappedVerts), len(newVertices)):
            newVert = newVertices[i]
            newVert.append(0)
            newVertTuple = tuple(newVert)
            terrainBM.verts.new(newVertTuple)

        terrainBM.verts.ensure_lookup_table()
        
        for triangle in t['triangles'].tolist():
            try:
                terrainBM.edges.new((terrainBM.verts[triangle[0]], terrainBM.verts[triangle[1]]))
            except ValueError:
                pass
            try:
                terrainBM.edges.new((terrainBM.verts[triangle[1]], terrainBM.verts[triangle[2]]))
            except ValueError:
                pass
            try:
                terrainBM.edges.new((terrainBM.verts[triangle[2]], terrainBM.verts[triangle[0]]))
            except ValueError:
                pass

        tmpMesh = bpy.data.meshes.new("tmpMesh")
        terrainBM.to_mesh(tmpMesh)
        tmpObject = bpy.data.objects.new("TerrainFragment", tmpMesh)
        
        tmpObject.vertex_groups.new(name="Roadside")
        tmpObject.vertex_groups["Roadside"].add(list(range(3, numOfBoundaryVertices)), 1.0, 'ADD')
        tmpObject.vertex_groups.new(name="Terrain")
        
        tmpObject.vertex_groups["Terrain"].add(list(range(4)), 1.0, 'ADD')
        tmpObject.vertex_groups["Terrain"].add(list(range(numOfBoundaryVertices, len(tmpObject.data.vertices))), 1.0, 'ADD')
        
        return tmpObject
    
    
    @staticmethod
#    def triangulize(vertices, edges):
    def triangulize(terrainBM):
        mappedVerts = list(map(lambda v: list(v.co.xy), list(terrainBM.verts)))
        numOfBoundaryVertices = len(mappedVerts)
        v = mappedVerts
        s = list(map(lambda e: [e.verts[0].index, e.verts[1].index], list(terrainBM.edges)))
#        s = list(map(lambda e: [e.vertices[0], e.vertices[1]], list(terrainBM.edges)))
        t = triangulate({'vertices': v, 'holes': [[11111, 11111]], 'segments': s}, 'qpa14.1')
        newVertices = t['vertices'].tolist()
        for i in range(len(mappedVerts), len(newVertices)):
            newVert = newVertices[i]
            newVert.append(0)
            newVertTuple = tuple(newVert)
            terrainBM.verts.new(newVertTuple)

        terrainBM.verts.ensure_lookup_table()

        for triangle in t['triangles'].tolist():
            try:
                terrainBM.edges.new((terrainBM.verts[triangle[0]], terrainBM.verts[triangle[1]]))
            except ValueError:
                pass
            try:
                terrainBM.edges.new((terrainBM.verts[triangle[1]], terrainBM.verts[triangle[2]]))
            except ValueError:
                pass
            try:
                terrainBM.edges.new((terrainBM.verts[triangle[2]], terrainBM.verts[triangle[0]]))
            except ValueError:
                pass

        tmpMesh = bpy.data.meshes.new("tmpMesh")
        terrainBM.to_mesh(tmpMesh)
        tmpObject = bpy.data.objects.new("TerrainFragment", tmpMesh)
        
        tmpObject.vertex_groups.new(name="Roadside")
        tmpObject.vertex_groups["Roadside"].add(list(range(numOfBoundaryVertices)), 1.0, 'ADD')
        tmpObject.vertex_groups.new(name="Terrain")
        tmpObject.vertex_groups["Terrain"].add(list(range(numOfBoundaryVertices, len(tmpObject.data.vertices))), 1.0, 'ADD')
        
        return tmpObject
    

class ExportPrep(bpy.types.Operator):
    bl_idname = "wm.export_prep"
    bl_label = "Prepare export"
    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        
        lColl = bpy.context.view_layer.layer_collection.children['COLONLY']
        bpy.context.view_layer.active_layer_collection = lColl
        for colliderObj in bpy.data.collections["FINAL"].objects:
            new_obj = colliderObj.copy()
            new_obj.data = colliderObj.data.copy()
            bpy.data.collections['COLONLY'].objects.link(new_obj)
#            colliderObj.select_set(True)
#            lColl = bpy.context.view_layer.layer_collection.children['COLONLY']
#            bpy.context.view_layer.active_layer_collection = lColl
#            bpy.ops.object.duplicate()
        
        
        mapObj = bpy.data.objects['Map']
        bpy.ops.mesh.separate(type='MATERIAL')
        
        objectsByMaterial = {}

        colonlyObjects = bpy.data.collections["COLONLY"].objects
        for colliderObj in colonlyObjects:
            colliderObj.select_set(True)
            bpy.ops.mesh.separate(type='MATERIAL')
        print("SEPARATION done")
        
        for colliderObj in bpy.data.collections["COLONLY"].objects:
            materialType = colliderObj.material_slots[0].material['materialType']
            if not materialType in objectsByMaterial:
                objectsByMaterial[materialType] = []
            objectsByMaterial[materialType].append(colliderObj)
        
        print("SORTING done")
        for key, objects in objectsByMaterial.items():
            bpy.ops.object.select_all(action='DESELECT')
            for o in objects:
                o.select_set(True)
            bpy.context.view_layer.objects.active = objects[0]
            bpy.ops.object.join()
            bpy.context.object.name = key + "-colonly"
        
        return {'FINISHED'}


def register():
    bpy.utils.register_class(HelloWorldPanel)
    bpy.utils.register_class(RunRoadBaking)
    bpy.utils.register_class(MySettings)
    bpy.utils.register_class(ExportPrep)
    
    bpy.types.Scene.myPropertiesasd = bpy.props.PointerProperty(type=MySettings)

def unregister():
    bpy.utils.unregister_class(HelloWorldPanel)
    bpy.utils.unregister_class(RunRoadBaking)
    bpy.utils.unregister_class(MySettings)
    bpy.utils.unregister_class(ExportPrep)
    del bpy.types.Scene.myPropertiesasd

if __name__ == "__main__":
    register()

#        self.report({'INFO'}, "BAKING ROADS...")
#        intersection = context.road_object
#        intersectionLocation = intersection.location
#        print("LOCATION: ", intersectionLocation)
        
#        bm = bmesh.new()
#        obj=bpy.context.object
##        if obj.mode == 'EDIT':
#        bm.from_mesh(obj.data)
#        print(len(bm.verts))
#        for v in bm.verts:
##            if v.select:
#            print(v.co)
#        else:
#            print("Object is not in edit mode.")


#        meshObjects = [o for o in bpy.context.scene.objects if o.type == "MESH" and o != context.road_object]
#        for obj in meshObjects:
#            dist = RunRoadBaking.distanceOfObjects(intersection, obj)
#            if dist < 112:
#                print("close enough: ", round(dist, 2), obj)
#                RunRoadBaking.drawLine(context, intersectionLocation, obj.location)
##                bpy.ops.mesh.primitive_uv_sphere_add(location=obj.location)
