import bpy, bmesh
import math, mathutils
import numpy as np
import random

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
        row.operator("wm.hello_world", text="Run road bakingASD")

class RunRoadBaking(bpy.types.Operator):
    bl_idname = "wm.hello_world"
    bl_label = "Minimal Operator"
    roadSegment: bpy.types.Object

    def execute(self, context):
        print("BAKING ROADS...")
        RunRoadBaking.cleanUpCreatedRoads()
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

        print("ROAD BAKING DONE")
        return {'FINISHED'}
    
    @staticmethod
    def connectRoadsInIntersection(roads, intersection): # fuck this specifically
        roadPairGenerator = createCircularIterator(roads)

        roadSides = []
        roadSidesBMesh = []
        intersectionEntrancePoints = []
        
        for roadPair in roadPairGenerator:
            '''
            draw 0th partial curve, save to lastLayer
            for layer in range(1, len(layers):
                layerCurve = ...
                layerCurve.to_mesh
                merge with 
                save to lastLayer
            '''
            
            
            
            p1 = roadPair[0].metadata["Left_0"][0]
            p2 = roadPair[1].metadata["Right_0"][0]
            h1 = roadPair[0].metadata["Left_0"][1]
            h2 = roadPair[1].metadata["Right_0"][1]

            layerCurveSegmentMesh = RunRoadBaking.createLayerCurveSegment(intersection.location, p1, p2, h1, h2)
            
            curve = layerCurveSegmentMesh
            roadSides.append(curve)

            firstVertex = curve.data.vertices[0]
            lastVertex = curve.data.vertices[-1]
            roadSides.append(curve)
            
            intersectionEntrancePoints.append((firstVertex, lastVertex))
            
            
            
            
            
            p1 = roadPair[0].metadata["Left_1"][0]
            p2 = roadPair[1].metadata["Right_1"][0]
            h1 = roadPair[0].metadata["Left_1"][1]
            h2 = roadPair[1].metadata["Right_1"][1]
            
            layerCurveSegmentMesh = RunRoadBaking.createLayerCurveSegment(intersection.location, p1, p2, h1, h2)
            
            curve = layerCurveSegmentMesh
            roadSides.append(curve)

            firstVertex = curve.data.vertices[0]
            lastVertex = curve.data.vertices[-1]
            roadSides.append(curve)
            
            intersectionEntrancePoints.append((firstVertex, lastVertex))
            
            
            
            
        
        intersectionBMesh = bmesh.new()
        for curve in roadSides:
            intersectionBMesh.from_mesh(curve.data)
        
#        for roadSide in roadSidesBMesh:
##            roadSideBMesh = bmesh.new()
##            roadSideBMesh.from_mesh(roadSide)
#            roadSide.select_set(True)
            
#            roadSidesBMesh.append(roadSideBMesh)
            
        bpy.ops.object.join()
        
#        for index, entrance in enumerate(intersectionEntrancePoints):
#            if index == 0:
#                p1 = intersectionEntrancePoints[0][0]
#                p2 = intersectionEntrancePoints[-1][1]
#            else:
#                p1 = intersectionEntrancePoints[index - 1][1]
#                p2 = intersectionEntrancePoints[index][0]
#                
#            p1.select = True
#            p2.select = True
#            
#            for v in intersectionBMesh.verts:
#                if v.co == p1.co:
#                    vert1 = v
#            for v in intersectionBMesh.verts:
#                if v.co == p2.co:
#                    vert2 = v
#                    
#            intersectionBMesh.edges.new((vert1, vert2))
            
        temp_mesh = bpy.data.meshes.new(".temp")
        intersectionBMesh.to_mesh(temp_mesh)
        ob = bpy.data.objects.new("joined bmeshes" + str(random.randint(11, 1111)), temp_mesh)
        bpy.data.collections["Shaite"].objects.link(ob)
        
        ob.location = intersection.location
        
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.editmode_toggle()
        
        bpy.ops.mesh.select_all(action='SELECT')
#        bpy.ops.mesh.fill()
        bpy.ops.object.editmode_toggle()

        for curve in roadSides:
            curve.select_set(True)
        
#            breakpoint()
            
#            bpy.ops.object.editmode_toggle()
#            bpy.ops.mesh.edge_face_add()
            
#            breakpoint()
#            print(roadPair[0].metadata)
#            RunRoadBaking.drawLine(p1, p2)
        bpy.ops.object.delete()

        
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
        
        
#        for i in range(math.floor(len(road.vertex_groups)/2)):
        left0Vertices  = [vert for vert in road.data.vertices if road.vertex_groups['Left_0'].index in [i.group for i in vert.groups]]
        right0Vertices = [vert for vert in road.data.vertices if road.vertex_groups['Right_0'].index in [i.group for i in vert.groups]]
        mappedCenterVertices = list(map(lambda vertex: road.matrix_world @ vertex.co, centerVertices))
        mappedLeft0Vertices  = list(map(lambda vertex: road.matrix_world @ vertex.co, left0Vertices))
        mappedRight0Vertices = list(map(lambda vertex: road.matrix_world @ vertex.co, right0Vertices))
         
        pairsOfClosestPoints["centerPoints"] = RunRoadBaking.closestPointPairInVertexGroup(mappedCenterVertices, intersection)
        pairA = RunRoadBaking.closestPointPairInVertexGroup(mappedLeft0Vertices, intersection)
        pairB = RunRoadBaking.closestPointPairInVertexGroup(mappedRight0Vertices, intersection)
        
        p1 = intersection.location.xy
        p2 = pairA[0].xy
        p3 = pairB[0].xy
        angle = angle_between(p3 - p1, p2 - p1)
        
        if angle > 180: # the left side is actually more to the left
            pairsOfClosestPoints["Left_0"]  = pairA
            pairsOfClosestPoints["Right_0"] = pairB
        else:
            pairsOfClosestPoints["Left_0"]  = pairB
            pairsOfClosestPoints["Right_0"] = pairA
        
        
        
        
        
        left1Vertices  = [vert for vert in road.data.vertices if road.vertex_groups['Left_1'].index in [i.group for i in vert.groups]]
        right1Vertices = [vert for vert in road.data.vertices if road.vertex_groups['Right_1'].index in [i.group for i in vert.groups]]
        mappedLeft1Vertices  = list(map(lambda vertex: road.matrix_world @ vertex.co, left1Vertices))
        mappedRight1Vertices = list(map(lambda vertex: road.matrix_world @ vertex.co, right1Vertices))
        
        pairA = RunRoadBaking.closestPointPairInVertexGroup(mappedLeft1Vertices, intersection)
        pairB = RunRoadBaking.closestPointPairInVertexGroup(mappedRight1Vertices, intersection)
        
        p1 = intersection.location.xy
        p2 = pairA[0].xy
        p3 = pairB[0].xy
        angle = angle_between(p3 - p1, p2 - p1)
        
        if angle > 180: # the left side is actually more to the left
            pairsOfClosestPoints["Left_1"]  = pairA
            pairsOfClosestPoints["Right_1"] = pairB
        else:
            pairsOfClosestPoints["Left_1"]  = pairB
            pairsOfClosestPoints["Right_1"] = pairA
        
        
        
        
        
        
        
#        p1 = intersection.location.xy
#        p2 = mathutils.Vector((intersection.location.x + 20, intersection.location.y))
#        p3a = pairA[0].xy
#        angleA = angle_between(p3a - p1, p2 - p1)
#        p3b = pairB[0].xy
#        angleB = angle_between(p3b - p1, p2 - p1)
#        
#        if angleA < angleB: # the left side is actually more to the left
#            pairsOfClosestPoints["Left_0"]  = pairA
#            pairsOfClosestPoints["Right_0"] = pairB
#        else:
#            pairsOfClosestPoints["Left_0"]  = pairB
#            pairsOfClosestPoints["Right_0"] = pairA
        
        
        
        
#        breakpoint()
#        RunRoadBaking.drawLine(p1, p2)
        
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
            p3 = road.metadata["centerPoints"][0].xy
            angle = angle_between(p3 - p1, p2 - p1) # angle = numpy.arccos((math.dist(p1, p2)**2 + math.dist(p1, p3)**2 - math.dist(p2, p3)**2) / (2 * math.dist(p1, p2) * math.dist(p1, p3)))
            roadsOrderedByAngles.append((road, angle))
        roadsOrderedByAngles.sort(key = lambda road: road[1])
        for road in roadsOrderedByAngles:
            print("ORDERED ROADS: ", road[0].object)
            orderedMapped.append(road[0])
        return orderedMapped

    @staticmethod
    def pairsOfRoads(roads):
        
        pass

    @staticmethod
    def setUpRoadModifiersAndConstraint(self, curve):
#        breakpoint()
        bpy.context.view_layer.objects.active = self.roadSegment
#        bpy.context.view_layer.objects.road = self.roadSegment
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
    def connectRoadsInIntersectionBAK(roads, intersectionLocation):
        roadPairings = RunRoadBaking.pairsOfRoads(roads)
        roadPairGenerator = createCircularIterator(roadPairings)
        for roadPair in roadPairGenerator:
            print(roadPair)
#        breakpoint()
    
        roadEnds = []
        
        for road in roads:
            print("Preparing road: ", road)
        
            road.select_set(True)
            bpy.context.view_layer.objects.road = road
            
            roadMesh = road.data
            roadBMesh = bmesh.new()
            roadBMesh.from_mesh(roadMesh)
            
            leftVertices = []
            rightVertices = []
            for v in roadMesh.vertices:
                for group in v.groups:
                    if group.group == 1:
                        leftVertices.append(v)
                    if group.group == 0:
                        rightVertices.append(v)
            
            closestLeftVertices = [leftVertices[0], leftVertices[1]]
            closestLeftDistances = [9999, 9999]
            closestRightVertices = [rightVertices[0], rightVertices[1]]
            closestRightDistances = [9999, 9999]

            # from closest to farthest:
            
            bpy.ops.object.mode_set(mode = 'EDIT')
            bpy.ops.mesh.select_mode(type = "VERT")
            
            leftVertices.sort(key = lambda v: (v.co - intersectionLocation).length)
            closestLeftVertices[0] = leftVertices[0]
            closestLeftVertices[1] = leftVertices[1]
            leftVertices[0].select = True
            leftVertices[1].select = True
            closestLeftDistances[0] = math.dist(intersectionLocation, leftVertices[0].co)
            closestLeftDistances[1] = math.dist(intersectionLocation, leftVertices[1].co)
            
            rightVertices.sort(key = lambda v: (v.co - intersectionLocation).length)
            closestRightVertices[0] = rightVertices[0]
            closestRightVertices[1] = rightVertices[1]
            rightVertices[0].select = True
            rightVertices[1].select = True
            closestRightDistances[0] = math.dist(intersectionLocation, rightVertices[0].co)
            closestRightDistances[1] = math.dist(intersectionLocation, rightVertices[1].co)
            
            breakpoint()
#            bpy.ops.object.mode_set(mode = 'OBJECT')
#            roadBMesh.to_mesh(roadMesh)
            
    #        for v in bm.verts:
    #            print(v.co)
    #            if v.select:

    #        bpy.ops.object.mode_set(mode = 'OBJECT')
    #        obj = bpy.context.road_object
    #        bpy.ops.mesh.select_all(action = 'DESELECT')
    #        bpy.ops.object.mode_set(mode = 'OBJECT')
    #        obj.data.vertices[0].select = True
    #        bpy.ops.object.mode_set(mode = 'EDIT') 
            
    #        breakpoint()
    #        bmesh.select_mode = {'VERT', 'EDGE', 'FACE'}
    #        bpy.ops.object.mode_set(mode = "EDIT")
    #        road.mode_set(mode = 'EDIT')


#1. give pair of roads
#    - left road:
#        - right side end vertex
#        - direction vector
#    - right road:
#        - left side end vertex
#        - direction vector
#    
#    (
#        {layers: [roadLayer]}, # 1. item is left road
#        {layers: [roadLayer]}  # 2. item is right road
#    )
#    
#    roadLayer: {
#        endVertex,
#        directionVector
#    }




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
