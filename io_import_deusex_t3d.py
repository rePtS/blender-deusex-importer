bl_info = {
    "name": "DeusEx T3D Import",
    "description": "Imports a DeusEx T3D file",
    "author": "Petr S.",
    "version": (1, 2),
    "blender": (2, 80, 0),
    "location": "File > Import",
    "support": "COMMUNITY",
    "category": "Import-Export"
    }


import bpy
import bmesh
import os
import mathutils
import colorsys
import math


PI = math.pi #3.141592653589793

# A coefficient for converting the rotation from the T3D format to the Blender format
ROTATION_RATE = PI * 2.0 / 65536.0

# Parses strings of the form "X=1234"
# and returns a pair of the string on the left (from the equal sign) and the number on the right
def parseAxisValue(axisValueString):
    splits = axisValueString.split('=')
    return splits[0], float(splits[1])


def parsePropertyValue(propertyValueString):
    splits = propertyValueString.split('=')
    if len(splits) == 0:
        return None, None
    elif len(splits) == 1:
        return splits[0], None
    else:
        return splits[0], splits[1]


# A simple method for roughly determining that objects intersect
def overlap(objA, objB):
    dimA = max(objA.dimensions)
    dimB = max(objB.dimensions)
    dist = objA.location - objB.location
    return (dist.x**2 + dist.y**2 + dist.z**2) < (dimA + dimB)**2


class Actor:

    def __init__(self, name):
        self._name = name
        self._object = None
        self._pptag = []
        self._loctag = []
        self._rottag = []
        self._scatag = []
        self._postscatag = []


    def setTransform(self):
        #FOR each vertex of each polygon of parsed brush DO:
        #   do MainScale ... x *= MainScale[x], y *= MainScale[y], z *= MainScale[z]
        #   do translation (-PrePivot[x], -PrePivot[y], -PrePivot[z])
        #   do rotation Yaw, Pitch, Roll
        #   do PostScale ... x *= PostScale[x], y *= PostScale[y], z *= PostScale[z]
        #   do TempScale ... x *= TempScale[x], y *= TempScale[y], z *= TempScale[z]
        #   do translation (Location[x], Location[y], Location[z])
        #ENDFOR

        # Applying scaling
        if len(self._scatag) > 0:
            scaleVec = mathutils.Vector((1.0, 1.0, 1.0))
            for item in self._scatag:
                axis, val = parseAxisValue(item)
                if axis == 'X':
                    scaleVec.x = val
                if axis == 'Y':
                    scaleVec.y = val
                if axis == 'Z':
                    scaleVec.z = val                    
            #bpy.context.object.scale = scaleVec
            self._object.scale = scaleVec

        # Set the central point of the actor.
        # It is relevant only for actors we upload mesh data.
        # Currently, there are some actors (for example, DeusexMover)
        # having both mesh and pivot points that do not need to be loaded yet
        if len(self._pptag) > 0 and self._object.data:
            prepivotVec = mathutils.Vector()
            for item in self._pptag:
                axis, val = parseAxisValue(item)
                if axis == 'X':
                    prepivotVec.x = val
                if axis == 'Y':
                    prepivotVec.y = -val
                if axis == 'Z':
                    prepivotVec.z = val

            me = self._object.data
            bm = bmesh.new()
            bm.from_mesh(me)
            for v in bm.verts:
                v.co -= prepivotVec
                
            bm.to_mesh(me)
            me.update()
        
        # Applying rotation
        if len(self._rottag) > 0:
            self._object.rotation_mode = 'XYZ'
            for item in self._rottag:
                axis, val = parseAxisValue(item)
                if axis == 'Roll':
                    self._object.rotation_euler[0] = val * ROTATION_RATE
                if axis == 'Pitch':
                    self._object.rotation_euler[1] = val * ROTATION_RATE
                if axis == 'Yaw':
                    self._object.rotation_euler[2] = -val * ROTATION_RATE

        # Applying scaling (in the old coordinates before rotation)
        if len(self._postscatag) > 0:
            postScaleVec = mathutils.Vector((1.0, 1.0, 1.0))
            for item in self._postscatag:
                axis, val = parseAxisValue(item)
                if axis == 'X':
                    postScaleVec.x = val
                if axis == 'Y':
                    postScaleVec.y = val
                if axis == 'Z':
                    postScaleVec.z = val
            
            eul = mathutils.Euler(self._object.rotation_euler, 'XYZ')
            postScaleVec.rotate(eul)
            self._object.scale.x *= abs(postScaleVec.x)
            self._object.scale.y *= abs(postScaleVec.y)
            self._object.scale.z *= abs(postScaleVec.z)

        # Specifying the location of the actor
        if len(self._loctag) > 0:
            locVec = mathutils.Vector()
            for item in self._loctag:
                axis, val = parseAxisValue(item)
                if axis == 'X':
                    locVec.x = val
                if axis == 'Y':
                    locVec.y = -val
                if axis == 'Z':
                    locVec.z = val
            self._object.location = locVec


    def parseLine(self, filelinetrim):
        if filelinetrim[0:10] == 'Location=(':
            locstring = filelinetrim[10:len(filelinetrim)-1]
            self._loctag = locstring.split(',')
                
        if filelinetrim[0:10] == 'PrePivot=(':
            ppstring = filelinetrim[10:len(filelinetrim)-1]
            self._pptag = ppstring.split(',')

        if filelinetrim[0:10] == 'Rotation=(':
            rotstring = filelinetrim[10:len(filelinetrim)-1]
            self._rottag = rotstring.split(',')
            
        if filelinetrim[0:18] == 'PostScale=(Scale=(':
            scalestring = filelinetrim[18:len(filelinetrim)-1]
            tmpstr = scalestring.split(')')
            self._postscatag = tmpstr[0].split(',')
            
        if filelinetrim[0:18] == 'MainScale=(Scale=(':
            scalestring = filelinetrim[18:len(filelinetrim)-1]
            tmpstr = scalestring.split(')')
            self._scatag = tmpstr[0].split(',')


    def parse(self, file):
        try:
            fileline = file.readline()
            while fileline:
                filelinetrim = fileline.strip()
                if self._object != None:
                    self.parseLine(filelinetrim)

                if filelinetrim.startswith('End Actor'):
                    if self._object != None:
                        self.setTransform()
                    break

                fileline = file.readline()
        except:
            print(self._name)
            raise


class Brush(Actor):

    def __init__(self, name):
        super().__init__(name)
        self._csgsubtract = False
        self._csgadd = False
        self._meshname = ''


    def parseLine(self, filelinetrim):
        super().parseLine(filelinetrim)

        if filelinetrim == "CsgOper=CSG_Subtract":
            self._csgsubtract = True

        if filelinetrim == "CsgOper=CSG_Add":
            self._csgadd = True

        if filelinetrim.startswith('Begin Brush'):
            splits = filelinetrim.split()
            for item in splits:
                prop, value = parsePropertyValue(item)
                if prop == 'Name':
                    self._meshname = value


    def parsePolygons(self, file):
        # Create mesh
        me = bpy.data.meshes.new(self._meshname)

        # Create object
        ob = bpy.data.objects.new(self._name, me)
        self._object = ob

        # Link object to scene
        bpy.context.scene.collection.objects.link(ob)

        # Get a BMesh representation
        bm = bmesh.new() # create an empty BMesh
        bm.from_mesh(me) # fill it in from a Mesh
        
        fileline = file.readline()
        while fileline:            
            filelinetrim = fileline.strip()            

            if filelinetrim.startswith('End PolyList'):
                break

            if filelinetrim.startswith('Begin Polygon'):
                vertexarray = []

            if filelinetrim.startswith('Vertex'):
                dataline = filelinetrim.split()
                xyz = dataline[1].split(',')
                x = float(xyz[0])
                y = -float(xyz[1])
                z = float(xyz[2])
                vert = ( x, y, z )
                vertexarray.append(bm.verts.new(vert))

            if filelinetrim.startswith('End Polygon'):
                # Initialize the index values of this sequence.
                bm.verts.index_update()
                vertexarray.reverse()
                vertextuple = tuple(vertexarray)
                # print('END POLYGON')
                bm.faces.new( vertextuple )

            fileline = file.readline()

        # The resulting mesh has duplicate vertices. We will delete them,
        # otherwise there will be problems with performing CSG operations
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)

        # Finish up, write the bmesh back to the mesh        
        bm.to_mesh(me)        
        bpy.context.view_layer.objects.active = ob


    def parse(self, file):
        fileline = file.readline()
        while fileline:
            filelinetrim = fileline.strip()
            self.parseLine(filelinetrim)        
        
            if filelinetrim.startswith('Begin PolyList'):
                if (self._csgadd or self._csgsubtract):
                    self.parsePolygons(file)

            if filelinetrim.startswith('End Actor'):
                if self._csgadd:
                    self.setTransform()

                    # just appending current object to the list of additive objects
                    Map.meshes.append(self._object)

                if self._csgsubtract:
                    self.setTransform()
                    
                    bpy.context.object.display_type = 'WIRE'

                    # scale is the key to good CSG operations - needed some overlap
                    bpy.ops.object.select_all(action='DESELECT')
                    self._object.select_set(True)
                    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
                    bpy.context.object.scale *= 1.0001

                    # go through the list of the additive objects
                    # and try to cut current substarctable object out of each one
                    for meshObj in Map.meshes:
                        if overlap(meshObj, self._object):
                            bpy.context.view_layer.objects.active = meshObj
                            bpy.ops.object.modifier_add(type='BOOLEAN')
                            modifier = bpy.context.object.modifiers["Boolean"]
                            modifier.object = self._object
                            modifier.solver = 'EXACT'
                            bpy.ops.object.modifier_apply(modifier="Boolean")
                
                    # delete current substarctable object, it is no longer needed
                    bpy.ops.object.delete()

                break

            fileline = file.readline()


class Light(Actor):

    def __init__(self, name):
        super().__init__(name)
        bpy.ops.object.light_add(type='POINT')
        bpy.context.object.name = name
        self._object = bpy.context.object
        self._hue = 0
        self._saturation = 0


    def parseLine(self, filelinetrim):
        super().parseLine(filelinetrim)
        prop, value = parsePropertyValue(filelinetrim)

        if prop == 'LightBrightness':
            self._object.data.energy = float(value)
        elif prop == 'LightHue':
            self._hue = float(value)
        elif prop == 'LightSaturation':
            self._saturation = float(value)
        elif prop == 'LightRadius':
            self._object.data.use_custom_distance = True
            self._object.data.cutoff_distance = float(value) * math.pow(Map.scale, 0.3) # scale light radius according map scale factor (with some fixes)
        elif prop == 'End Actor':
            self._object.data.color = colorsys.hsv_to_rgb(self._hue / 255.0, self._saturation / 255.0, 1.0)


class SpotLight(Actor):

    def __init__(self, name):
        super().__init__(name)
        bpy.ops.object.light_add(type='SPOT')
        bpy.context.object.name = name        
        self._object = bpy.context.object
        self._hue = 0
        self._saturation = 0

        #self._object.parent = Map.meshes[0]
        #self._object.matrix_parent_inverse = Map.meshes[0].matrix_world.inverted()


    def setTransform(self):
        # Skip spotlight rotation
        self._rottag = [];
        super().setTransform();


    def parseLine(self, filelinetrim):
        super().parseLine(filelinetrim)
        prop, value = parsePropertyValue(filelinetrim)

        if prop == 'LightBrightness':
            self._object.data.energy = float(value)
        elif prop == 'LightHue':
            self._hue = float(value)
        elif prop == 'LightSaturation':
            self._saturation = float(value)
        elif prop == 'LightRadius':
            self._object.data.use_custom_distance = True
            self._object.data.cutoff_distance = float(value) * math.pow(Map.scale, 0.3) # scale light radius according map scale factor (with some fixes)
        elif prop == 'LightCone':
            spot_ratio = float(value) / 255.0
            self._object.data.spot_size = spot_ratio * PI
            self._object.data.spot_blend = (1.0 - spot_ratio) * 0.7 + 0.15
        elif prop == 'End Actor':
            self._object.data.color = colorsys.hsv_to_rgb(self._hue / 255.0, self._saturation / 255.0, 1.0)


class Placeholder(Actor):

    def __init__(self, name, actorClass):
        super().__init__(name)
        if Map.importUnvisuals:
            bpy.ops.object.empty_add(type='PLAIN_AXES')
            bpy.context.object.name = "proxy_" + name
            # add custom attribute
            bpy.context.object['proxy_smname'] = actorClass
            self._object = bpy.context.object


class Map:

    importUnvisuals = False
    scale = 1.0
    meshes = []

    def __init__(self, scenescale, importUnvisuals):
        # Main mesh
        bpy.ops.mesh.primitive_cube_add(size=28000)
        bpy.context.object.name = "WorldCSG"
        Map.meshes.append(bpy.context.object)
        Map.scale = scenescale
        Map.importUnvisuals = importUnvisuals

    def parse(self, file):
        fileline = file.readline()
        while fileline:
            if fileline.startswith('Begin Actor'):
                                
                actorClass = ''
                actorName = ''

                # Get the type and name of the actor
                splits = fileline.split()
                for item in splits:
                    prop, value = parsePropertyValue(item)
                    if prop == 'Class':
                        actorClass = value
                    if prop == 'Name':
                        actorName = value

                if actorClass == 'Spotlight':
                    spotLight = SpotLight(actorName)
                    spotLight.parse(file)
                elif actorClass == 'Light':
                    light = Light(actorName)
                    light.parse(file)
                elif actorClass == 'Brush':
                    brush = Brush(actorName)
                    brush.parse(file)
                else:
                    placeholder = Placeholder(actorName, actorClass)
                    placeholder.parse(file)

            fileline = file.readline()

        # Scale all the objects, if necessary
        if Map.scale != 1.0:
            for obj in bpy.context.scene.objects:
                obj.location *= Map.scale
                obj.scale *= Map.scale


# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, FloatProperty, BoolProperty
from bpy.types import Operator


class ImportT3dData(Operator, ImportHelper):
    """Import an Unreal Engine T3D scene file into Blender"""
    bl_idname = "import_t3d.some_data"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import T3D Data"

    # ImportHelper mixin class uses this
    filename_ext = ".t3d"

    # filter_glob = StringProperty(
    filter_glob: StringProperty(
            default="*.t3d",
            options={'HIDDEN'},
            maxlen=255,  # Max internal buffer length, longer would be clamped.
            )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    # scenescale = FloatProperty(
    scenescale: FloatProperty(
            name="Import Scale",
            description="scale imported scene",
            default=1.0,
            min=0.0001
            )

    # Flag if we should import positions of the unvisual objects from T3D-file
    importUnvisuals: BoolProperty(
            name="Import Unvisuals",
            description="import positions of triggers, sounds, path nodes, etc.",
            default=False
            )

    def execute(self, context):
        map = Map(self.scenescale, self.importUnvisuals)
        with open(self.filepath, 'r', encoding='utf-8') as file:
            map.parse(file)

        return {'FINISHED'}


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportT3dData.bl_idname, text="DeusEx T3D (.t3d)")


classes = [
    ImportT3dData
]


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()
