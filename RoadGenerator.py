import bpy, bmesh
import math, mathutils
import numpy as np
import random
import copy
from triangle import *

def createCircularIterator(roads):
    iterRoads = iter(roads)
    returnRoads = [next(iterRoads)]

    for road in iterRoads:
        returnRoads.append(road)
        yield returnRoads
        returnRoads.pop(0)

    returnRoads.append(roads[0])
    yield returnRoads

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
    bl_label = "Hello World Panel"
    bl_idname = "OBJECT_PT_helloasdasd"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    def draw(self, context):
        layout = self.layout
        obj = context.object
        row = layout.row()
        row.label(text="Hello world!", icon='WORLD_DATA')
        row = layout.row()
        row.label(text="Active object is: " + obj.name)
        row = layout.row()
        row.prop(obj, "name")
        row = layout.row()
        row.operator("mesh.primitive_uv_sphere_add", text="Add intersection")
        row = layout.row()
        row.operator("wm.hello_world", text="Run road baking")

class RunRoadBaking(bpy.types.Operator):
    bl_idname = "wm.hello_world"
    bl_label = "Minimal Operator"
    roadSegment: bpy.types.Object
    
    def execute(self, context):
        print("BAKING ROADS...")
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
                    print(road.name, distance)
                    
                    if distance < RANGE_OF_INTERSECTION:
                        roadsCloseToIntersection.append(road)
                bm.clear()
            
            if len(roadsCloseToIntersection) > 0:
                print("Connect roads")
                
                roadsWithMetadata = RunRoadBaking.pairRoadsToTheirIntersectionPoints(roadsCloseToIntersection, intersection)
                orderedRoads = RunRoadBaking.orderRoadsAroundIntersectionCCW(roadsWithMetadata, intersection)
                RunRoadBaking.connectRoadsInIntersection(orderedRoads, intersection)
        
        roadNetwork = RunRoadBaking.joinRoadsAndIntersections()
        terrainFragments = RunRoadBaking.createTerrainFragments(roadNetwork)
        
        roadNetwork.select_set(False)
#        bpy.context.view_layer.objects.active = roadNetwork
        
        
        
        
#        for terrainFragment in terrainFragments:
#            terrainFragment.select = True
##            bpy.context.view_layer.objects.active = terrainFragment
#            bpy.ops.object.join()
##            bpy.data.collections["Terrain"].objects.link(terrainFragment)
##        temp_mesh = bpy.data.meshes.new(".temp")
##        mergedBM.to_mesh(temp_mesh)
##        mergerObject = bpy.data.objects.new("FINALTERRAIN" + str(random.randint(11, 1111)), temp_mesh)
##        mergerObject.location = roadNetwork.location
#        RunRoadBaking.shrinkwrapTerrain(roadNetwork)
#        bpy.data.collections["Shaite"].objects.link(roadNetwork)
        
        
#        mergedBM = bmesh.new()
#        mergedBM.from_mesh(roadNetwork.data)
#        for terrainFragment in terrainFragments:
#            bpy.data.collections["Terrain"].objects.link(terrainFragment)
#            RunRoadBaking.shrinkwrapTerrain(terrainFragment)
#            mergedBM.from_mesh(terrainFragment.data)
#        temp_mesh = bpy.data.meshes.new(".temp")
#        mergedBM.to_mesh(temp_mesh)
#        mergerObject = bpy.data.objects.new("FINALTERRAIN" + str(random.randint(11, 1111)), temp_mesh)
#        mergerObject.location = roadNetwork.location
#        bpy.data.collections["Shaite"].objects.link(mergerObject)
        
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
        
        print("ROAD BAKING DONE")
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

        roadSides = []
        roadSidesBMesh = []
        roadSidesMesh = []
        intersectionEntranceCenterPoints = []
        intersectionEntranceLayerPoints = []
        
        roadSegments_BMesh = []
        roadSegments_Mesh = []
        roadSegmentObjects = []
        
        '''
        roadSegments = []
        
        for roadPair:
            * create Curve 0
            * convert to mesh
            
            for layers:         # roadSegmentLayers
                * create Curve {index}
                * convert to mesh
                * merge into base mesh
                * add side edges
                
                * fill with faces between Curve_{index - 1} and Curve_{index}
        
        merge roadSegments
        '''
        
        for roadPair in roadPairGenerator:
            roadSegmentLayers = []
            roadSegmentBMesh = bmesh.new()
            
            '''
            for layer in range(1, len(layers):
            '''
            
            p1 = roadPair[0].metadata["Left_0"][0]
            p2 = roadPair[1].metadata["Right_0"][0]
            h1 = roadPair[0].metadata["Left_0"][1]
            h2 = roadPair[1].metadata["Right_0"][1]

            layerCurveSegmentMesh = RunRoadBaking.createLayerCurveSegment(intersection.location, p1, p2, h1, h2)
            
            curve = layerCurveSegmentMesh
            curve.vertex_groups.new(name="Curve_0")
            curve.vertex_groups["Curve_0"].add(list(map(lambda v: v.index, curve.data.vertices)), 1.0, 'ADD')
            roadSides.append(curve)
            roadSegmentLayers.append(curve)
            roadSegmentBMesh.from_mesh(curve.data)
            roadSegmentMesh = curve
#            roadSegmentObject = bpy.data.objects.new("RoadSegment" + str(random.randint(11, 1111)), roadSegmentMesh)
            roadSegmentObject = curve
            
            bpy.ops.object.join()
            
            
            firstVertex = curve.data.vertices[0]
            lastVertex = curve.data.vertices[-1]
            
            
            previousCurveEndVertices = (copy.deepcopy(firstVertex.co), copy.deepcopy(lastVertex.co))
#            intersectionEntrancePoints.append((firstVertex, lastVertex))
            
            
            p1 = roadPair[0].metadata["Left_1"][0]
            p2 = roadPair[1].metadata["Right_1"][0]
            h1 = roadPair[0].metadata["Left_1"][1]
            h2 = roadPair[1].metadata["Right_1"][1]
            
            layerCurveSegmentMesh = RunRoadBaking.createLayerCurveSegment(intersection.location, p1, p2, h1, h2)
            
            curve = layerCurveSegmentMesh
            curve.vertex_groups.new(name="Curve_1")
            curve.vertex_groups["Curve_1"].add(list(map(lambda v: v.index, curve.data.vertices)), 1.0, 'ADD')
            roadSides.append(curve)
            roadSegmentLayers.append(curve)
            roadSegmentBMesh.from_mesh(curve.data)
            
            roadSegmentMesh.select_set(True)
            roadSegmentMesh = curve
#            toBeMerged = bpy.data.objects.new("TMP_RoadSegment" + str(random.randint(11, 1111)), roadSegmentMesh)
            toBeMerged = curve

            
            firstVertex = curve.data.vertices[0]
            lastVertex = curve.data.vertices[-1]
            
            bpy.context.view_layer.objects.active = roadSegmentObject
            roadSegmentObject.select_set(True)
            toBeMerged.select_set(True)
            bpy.ops.object.join()
            
            # add edges between layers
            roadSegmentObject.data.edges.add(1)
            edgeIndex = len(roadSegmentObject.data.edges) - 1
            p1 = previousCurveEndVertices[0]
            p2 = firstVertex.co
            for v in roadSegmentObject.data.vertices:
                if v.co == p1:
                    vert1 = v.index
            for v in roadSegmentObject.data.vertices:
                if v.co == p2:
                    vert2 = v.index
            roadSegmentObject.data.edges[edgeIndex].vertices[0] = vert1
            roadSegmentObject.data.edges[edgeIndex].vertices[1] = vert2
#            roadSegmentObject.edges.new((vert1, vert2))
#            roadSegments.append(roadSegmentLayers)

            roadSegmentObject.data.edges.add(1)
            edgeIndex = len(roadSegmentObject.data.edges) - 1
            p1 = lastVertex.co
            p2 = previousCurveEndVertices[1]
            for v in roadSegmentObject.data.vertices:
                if v.co == p1:
                    vert1 = v.index
            for v in roadSegmentObject.data.vertices:
                if v.co == p2:
                    vert2 = v.index
            roadSegmentObject.data.edges[edgeIndex].vertices[0] = vert1
            roadSegmentObject.data.edges[edgeIndex].vertices[1] = vert2
#            roadSegmentObject.edges.new((vert1, vert2))
#            roadSegments.append(roadSegmentLayers)
            

            
            intersectionEntranceCenterPoints.append((firstVertex, lastVertex))


#            intersectionEntranceLayerPoints.append((previousCurveEndVertices[0].copy(), firstVertex.co.copy()))
#            intersectionEntranceLayerPoints.append((lastVertex.co.copy(), previousCurveEndVertices[1].copy()))


            
#            if len(intersectionEntranceCenterPoints) > 0:
#                roadSegmentObject.data.edges.add(1)
#                edgeIndex = len(roadSegmentObject.data.edges) - 1
#                p1 = firstVertex
#                p2 = intersectionEntranceCenterPoints[-1][1]
#                    
#    #            p1.select = True
#    #            p2.select = True
#                
#                for v in roadSegmentObject.data.vertices:
#                    if v.co == p1.co:
#                        vert1 = v.index
#                for v in roadSegmentObject.data.vertices:
#                    if v.co == p2.co:
#                        vert2 = v.index
#                roadSegmentObject.data.edges[edgeIndex].vertices[0] = vert1
#                roadSegmentObject.data.edges[edgeIndex].vertices[1] = vert2
#    #            roadSegmentBMesh.edges.new((vert1, vert2))
#                
#                bpy.ops.object.editmode_toggle()
#                bpy.ops.object.editmode_toggle()
            
            
            
            
            
            
            
            
            
            roadSegments_BMesh.append(roadSegmentBMesh)
            roadSegmentObjects.append(roadSegmentObject)
        
        
        
#        roadSegmentObject.data.edges.add(1)
#        edgeIndex = len(roadSegmentObject.data.edges) - 1
#        p1 = firstVertex
#        p2 = intersectionEntranceCenterPoints[-1][1]
#            
##            p1.select = True
##            p2.select = True
#        
#        for v in roadSegmentObject.data.vertices:
#            if v.co == p1.co:
#                vert1 = v.index
#        for v in roadSegmentObject.data.vertices:
#            if v.co == p2.co:
#                vert2 = v.index
#        roadSegmentObject.data.edges[edgeIndex].vertices[0] = vert1
#        roadSegmentObject.data.edges[edgeIndex].vertices[1] = vert2
##            roadSegmentBMesh.edges.new((vert1, vert2))
#        
#        bpy.ops.object.editmode_toggle()
#        bpy.ops.object.editmode_toggle()
            
        
        
        
        
        intersectionBMesh = bmesh.new()
        
                

        
        
#        for roadSegment in roadSegments:
#            iter_roadSegmentLayers = iter(roadSegmentLayers)
#            firstLayer = next(roadSegmentLayers)
#            
#            for layer in iter_roadSegmentLayers:
#                
#                intersectionBMesh.from_mesh(curve.data)
#    #        for roadSide in roadSidesBMesh:
#    ##            roadSideBMesh = bmesh.new()
#    ##            roadSideBMesh.from_mesh(roadSide)
#    #            roadSide.select_set(True)
#                
#    #            roadSidesBMesh.append(roadSideBMesh)
#            bpy.ops.object.join()
        
        
#        for curve in roadSides:
#            intersectionBMesh.from_mesh(curve.data)
#        for roadSide in roadSidesBMesh:
###            roadSideBMesh = bmesh.new()
###            roadSideBMesh.from_mesh(roadSide)
#            roadSide.select_set(True)
#            
#            roadSidesBMesh.append(roadSideBMesh)
#        bpy.ops.object.join()
        
        
        for roadSegmentBMesh in roadSegments_BMesh:
            tmpMesh = bpy.data.meshes.new("tmpMesh")
            roadSegmentBMesh.to_mesh(tmpMesh)
            intersectionBMesh.from_mesh(tmpMesh)
        
        
        
        
        
        temp_mesh = bpy.data.meshes.new(".temp")
        mergerObject = bpy.data.objects.new("IntersectionCLASSIC" + str(random.randint(11, 1111)), temp_mesh)
        bpy.data.collections["Shaite"].objects.link(mergerObject)
#        terrain = bpy.data.objects.new("empty", None)
        
        for roadSegmentObject in roadSegmentObjects:
#            bpy.context.view_layer.objects.active = mergerObject
#            breakpoint()
            roadSegmentObject.select_set(True)
#            bpy.ops.mesh.select_all(action='SELECT')
#            bpy.ops.mesh.fill()

#            bpy.ops.object.editmode_toggle()
#            bpy.ops.object.editmode_toggle()
            
            mergerObject.select_set(True)
            bpy.ops.object.join()
            
            mergerObject = bpy.context.object
        
#        bpy.data.collections["Shaite"].objectsROADOBJ(mergerObject)
        








        
        for index, entrance in enumerate(intersectionEntranceCenterPoints):
            if index == 0:
                p1 = intersectionEntranceCenterPoints[0][0]
                p2 = intersectionEntranceCenterPoints[-1][1]
            else:
                p1 = intersectionEntranceCenterPoints[index - 1][1]
                p2 = intersectionEntranceCenterPoints[index][0]
                
            roadSegmentObject = mergerObject
            roadSegmentObject.data.edges.add(1)
            edgeIndex = len(roadSegmentObject.data.edges) - 1
            
            for v in roadSegmentObject.data.vertices:
                if v.co == p1.co:
                    vert1 = v.index
            for v in roadSegmentObject.data.vertices:
                if v.co == p2.co:
                    vert2 = v.index
            roadSegmentObject.data.edges[edgeIndex].vertices[0] = vert1
            roadSegmentObject.data.edges[edgeIndex].vertices[1] = vert2

        
        
                    
#            if len(intersectionEntranceCenterPoints) > 0:
#                roadSegmentObject.data.edges.add(1)
#                edgeIndex = len(roadSegmentObject.data.edges) - 1
#                p1 = firstVertex
#                p2 = intersectionEntranceCenterPoints[-1][1]
#                    
#    #            p1.select = True
#    #            p2.select = True
#                
#                for v in roadSegmentObject.data.vertices:
#                    if v.co == p1.co:
#                        vert1 = v.index
#                for v in roadSegmentObject.data.vertices:
#                    if v.co == p2.co:
#                        vert2 = v.index
#                roadSegmentObject.data.edges[edgeIndex].vertices[0] = vert1
#                roadSegmentObject.data.edges[edgeIndex].vertices[1] = vert2
#    #            roadSegmentBMesh.edges.new((vert1, vert2))
#                
#                bpy.ops.object.editmode_toggle()
#                bpy.ops.object.editmode_toggle()
        
        
        
        
        
        
        
        
#        intersectionMesh = bpy.data.meshes.new("intersectionMesh")
#        intersectionBMesh.to_mesh(intersectionMesh)
##        intersectionMesh = intersectionBMesh.to_mesh(tmpIntersectionMesh)
#        intersectionObject = bpy.data.objects.new("ASDmergedRoadSegmentMesh", intersectionMesh)
#        bpy.data.collections["Shaite"].objects.link(intersectionObject)
        
#        breakpoint()
        


#        for curve in roadSides:
#            curve.select_set(True)
#        
##            breakpoint()
#            
##            bpy.ops.object.editmode_toggle()
##            bpy.ops.mesh.edge_face_add()
#            
##            breakpoint()
##            print(roadPair[0].metadata)
##            RunRoadBaking.drawLine(p1, p2)
#        bpy.ops.object.delete()

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.fill()
        bpy.ops.object.editmode_toggle()

        
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
#            breakpoint()
            roadElement = RoadElement(road, setsOfClosestPoints)
            roadsWithMetadata.append(roadElement)
            
        return roadsWithMetadata
    
    
    @staticmethod
    def getClosestPointsToIntersection(road, intersection):
        print(road)
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
#        breakpoint()
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
            print("ORDERED ROADS: ", road[0].object)
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
        print("LINE CREATED")
    
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
        
            print('SELECTED verts: ', len(selected_verts))
            
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
                        print('FOUND VERTEX ON EDGE')
                        break
                if len(vertexPairOnEdge) > 1:
                    print('Found EDGE')
                    break
            
            print('vertexPairOnEdge: ', len(vertexPairOnEdge))
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
                print('OUTER GENERATE')
                corners = [[-120, -110], [200, -110], [220, 220], [-120, 220]]
                hole = [110, 110]
                
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

        t = triangulate({'vertices': v, 'holes': [hole], 'segments': s}, 'qpa4.1')
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
        t = triangulate({'vertices': v, 'holes': [[11111, 11111]], 'segments': s}, 'qpa4.1')
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


def register():
    bpy.utils.register_class(HelloWorldPanel)
    bpy.utils.register_class(RunRoadBaking)

def unregister():
    bpy.utils.unregister_class(HelloWorldPanel)
    bpy.utils.unregister_class(RunRoadBaking)

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
