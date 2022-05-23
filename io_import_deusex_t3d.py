bl_info = {
    "name": "DeusEx T3D Import",
    "description": "Imports a DeusEx T3D file",
    "author": "Petr S.",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "File > Import",
    "support": "COMMUNITY",
    "category": "Import-Export"
    }


import bpy
import bmesh
import os
import mathutils


# Коэффициент для преобразования вращения формата T3D в формат Blender
ROTATION_RATE = 3.141592653589793 * 2.0 / 65536.0

# Парсит строки вида "X=1234"
# и возвращает пару из строки слева (от знака равно) и числа справа
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


class Actor:

    def __init__(self, name):
        self._name = name
        self._object = None
        self._pptag = []
        self._loctag = []
        self._rottag = []
        self._scatag = []
        self._postscatag = []


    def setTransform(self, scenescale=1.0):
        #FOR each vertex of each polygon of parsed brush DO:
        #   do MainScale ... x *= MainScale[x], y *= MainScale[y], z *= MainScale[z]
        #   do translation (-PrePivot[x], -PrePivot[y], -PrePivot[z])
        #   do rotation Yaw, Pitch, Roll
        #   do PostScale ... x *= PostScale[x], y *= PostScale[y], z *= PostScale[z]
        #   do TempScale ... x *= TempScale[x], y *= TempScale[y], z *= TempScale[z]
        #   do translation (Location[x], Location[y], Location[z])
        #ENDFOR

        # Применяем масштабирование
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

        # Устанавливаем центральную точку актора
        # Актуально только для тех акторов, для которых загружаем данные о меше.
        # В настоящее время, есть акторы (например, DeusexMover), у которых есть и
        # мэш и pivot-точки, но которые пока не требуется загружать
        if len(self._pptag) > 0 and self._object.data:
            prepivotVec = mathutils.Vector()
            for item in self._pptag:
                axis, val = parseAxisValue(item)
                if axis == 'X':
                    prepivotVec.x = val * scenescale
                if axis == 'Y':
                    prepivotVec.y = -val * scenescale
                if axis == 'Z':
                    prepivotVec.z = val * scenescale

            me = self._object.data
            bm = bmesh.new()
            bm.from_mesh(me)
            for v in bm.verts:
                v.co -= prepivotVec
                
            bm.to_mesh(me)
            me.update()
        
        # Применяем вращение
        if len(self._rottag) > 0:
            self._object.rotation_mode = 'ZYX'
            for item in self._rottag:
                axis, val = parseAxisValue(item)
                if axis == 'Roll':
                    self._object.rotation_euler[0] = -val * ROTATION_RATE
                if axis == 'Pitch':
                    self._object.rotation_euler[1] = val * ROTATION_RATE
                if axis == 'Yaw':
                    self._object.rotation_euler[2] = -val * ROTATION_RATE

        # Применяем масштабирование (в старых координатах до вращения)
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

        # Указываем местоположения актора
        if len(self._loctag) > 0:
            locVec = mathutils.Vector()
            for item in self._loctag:
                axis, val = parseAxisValue(item)
                if axis == 'X':
                    locVec.x = val * scenescale
                if axis == 'Y':
                    locVec.y = -val * scenescale
                if axis == 'Z':
                    locVec.z = val * scenescale
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
                self.parseLine(filelinetrim)

                if filelinetrim.startswith('End Actor'):
                    self.setTransform()
                    break

                fileline = file.readline()
        except:
            print(self._name)
            raise


class Brush(Actor):

    BOONAME = "Boolean"

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


    def parsePolygons(self, file, scenescale=1.0):
        # Create mesh
        me = bpy.data.meshes.new(self._meshname)

        # Create object
        ob = bpy.data.objects.new(self._name, me)
        self._object = ob

        # Link object to scene
        # bpy.context.scene.objects.link(ob)
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
                x = float(xyz[0]) * scenescale
                y = -float(xyz[1]) * scenescale
                z = float(xyz[2]) * scenescale
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

        # Полученный меш имеет дублирующиеся вершины. Удалим их,
        # иначе будут проблемы при выполнении CSG-операций
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)

        # Finish up, write the bmesh back to the mesh        
        bm.to_mesh(me)        
        bpy.context.view_layer.objects.active = ob


    def parse(self, file, worldCSG):
        fileline = file.readline()
        while fileline:
            filelinetrim = fileline.strip()
            self.parseLine(filelinetrim)        
        
            if filelinetrim.startswith('Begin PolyList'):
                if (self._csgadd or self._csgsubtract):
                    self.parsePolygons(file)

            if filelinetrim.startswith('End Actor'):
                if (self._csgadd or self._csgsubtract):
                    self.setTransform()

                if self._csgadd:
                    bpy.ops.object.select_all(action='DESELECT')
                    self._object.select_set(True)
                    bpy.context.object.display_type = 'WIRE'
                    bpy.ops.object.duplicate()
                    worldCSG.select_set(True)
                    bpy.context.view_layer.objects.active = worldCSG                    
                    bpy.ops.object.join()

                if self._csgsubtract:
                    bpy.context.object.display_type = 'WIRE'

                    #scale is the key to good booleans - needed some overlap
                    #overwriting transform place in xfrom function
                    bpy.ops.object.select_all(action='DESELECT')
                    self._object.select_set(True)
                    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
                    bpy.context.object.scale *= 1.0001

                    bpy.context.view_layer.objects.active = worldCSG
                    bpy.ops.object.modifier_add(type='BOOLEAN')
                    bpy.context.object.modifiers[Brush.BOONAME].object = self._object
                    bpy.context.object.modifiers[Brush.BOONAME].solver = 'EXACT'
                    bpy.context.object.modifiers[Brush.BOONAME].use_hole_tolerant = True
                    #bpy.context.object.modifiers[BOONAME].use_self = True
                    bpy.ops.object.modifier_apply(modifier="Boolean")

                break

            fileline = file.readline()


class Light(Actor):

    def __init__(self, name):
        super().__init__(name)
        bpy.ops.object.light_add(type='POINT')
        bpy.context.object.name = name
        self._object = bpy.context.object


class SpotLight(Actor):

    def __init__(self, name):
        super().__init__(name)
        bpy.ops.object.lamp_add(type='SPOT')
        bpy.context.object.name = name
        self._object = bpy.context.object


class Placeholder(Actor):

    def __init__(self, name, actorClass):
        super().__init__(name)
        bpy.ops.object.empty_add(type='PLAIN_AXES')
        bpy.context.object.name = "ue4proxy_" + name
        # add custom attribute
        bpy.context.object['proxy_smname'] = actorClass
        self._object = bpy.context.object


class Map:

    def __init__(self):
        scenescale = 1.0
        bpy.ops.mesh.primitive_cube_add(size=7000*scenescale*4)
        bpy.context.object.name = "WorldCSG"
        self._worldCSG = bpy.context.object

    def parse(self, file):
        fileline = file.readline()
        while fileline:
            if fileline.startswith('Begin Actor'):
                                
                actorClass = ''
                actorName = ''

                # Получаем тип и наименование актора
                splits = fileline.split()
                for item in splits:
                    prop, value = parsePropertyValue(item)
                    if prop == 'Class':
                        actorClass = value
                    if prop == 'Name':
                        actorName = value

                if actorClass == 'SpotLight':
                    spotLight = SpotLight(actorName)
                    spotLight.parse(file)
                elif actorClass == 'Light':
                    light = Light(actorName)
                    light.parse(file)
                elif actorClass == 'Brush':
                    brush = Brush(actorName)
                    brush.parse(file, self._worldCSG)
                else:
                    placeholder = Placeholder(actorName, actorClass)
                    placeholder.parse(file)

            fileline = file.readline()

        # Проскейлим все объекты
        for obj in bpy.context.scene.objects:
            obj.location *= 0.01
            obj.scale *= 0.01


# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, FloatProperty
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
            description="scale imported xyz values",
            #default=0.01,
            default=1.0,
            min=0.0001
            )

    def execute(self, context):
        map = Map()
        with open(self.filepath, 'r', encoding='utf-8') as file:
            map.parse(file)

        return {'FINISHED'}


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportT3dData.bl_idname, text="T3D Import Operator")


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
