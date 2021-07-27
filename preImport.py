import bpy
import math
import os.path
import glob
from xml.etree import cElementTree as ElementTree
from ast import literal_eval as make_tuple
from datetime import datetime

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


context = bpy.context 
scene = context.scene
import_basedir = 'X:\\SC312\Data\\'
# xmlPath = importBaseDir + 'Objects/Spaceships/Ships/ANVL/Pisces/anvl_pisces_ext_XL.mtl'
option_brushes = True
option_component = True
option_lights = True
option_spawn = False
option_preconvert = False
option_fixorphans = True
option_findmtls = True
option_import = True
option_findmats = True
log_files = "Geometry"
log_mats = "Materials"
log_errors = "Errors"
#xml_parent = './/*[@Prefab]'
#xml_parent = './Prefab/Objects/Object/Components/Component/Properties'
xml_parent = './PrefabLibrary/Prefab/Objects/Object'
xml_property = 'Prefab'



def parseXML(xml_path):
    file_list = []
    mat_list = []
    try:
        xml_root = ElementTree.parse(xml_path).getroot()
    except Exception as e:
        print('Unable to open XML: ' + str(e))
        raise
    
    prefab_collection = (bpy.data.collections.get(stripPath(xml_path)) or bpy.data.collections.new(stripPath(xml_path)))
    if not scene.collection.children.get(stripPath(xml_path)): scene.collection.children.link(prefab_collection)
    viewlayer = context.view_layer.layer_collection.children.get((stripPath(xml_path)))
    if viewlayer: context.view_layer.active_layer_collection = viewlayer
    
    for element in xml_root.findall('.//*[@Prefab]'):
        filename = element.attrib['Prefab']
        path = import_basedir + filename.lower()
        path = path.replace('\\', '/')
        path = path.lower()
        if path not in file_list:
            file_list.append(path)        
        
    for element in xml_root.findall('.//*[@Material]'):
        filename = element.attrib['Material']
        path = import_basedir + filename.lower() + '.mtl'
        path = path.replace('\\', '/')
        path = path.lower()
        if path not in mat_list:
            mat_list.append(path)            

    
    if option_import:
        log_text = (bpy.data.texts.get(log_errors) or bpy.data.texts.new(log_errors))
        for file in file_list:
            dae_filename = file
            dae_filename = dae_filename.replace('.cgf', '.dae')
            dae_filename = dae_filename.replace('.cga', '.dae')
            try:
                bpy.ops.wm.collada_import(filepath=dae_filename)     
            except Exception as e:
                #print("Import Error: " + file + "\n")
                log_text.write("Import Failed: " + file + "\n")
                continue
            import_obj = bpy.context.selected_objects
            for obj in import_obj:
                obj['Filename'] = dae_filename
                obj['Material'] = readMtlfromDAE(dae_filename)
                if obj.type == 'MESH':
                    obj.data['Filename'] = dae_filename
                try:
                    bpy.data.collections[xml_path].objects.link(obj)
                except:
                    pass                                 
                
    if option_fixorphans:
        for obj in scene.objects[:]:
            if 'Merged' in obj.name:
                filename = obj['Filename'].rpartition('/')[2]
                filename = filename.replace('.dae', '')
                #print(filename)
                obj.name = filename + '.Merged'
                if scene.objects.get(filename) and scene.objects.get(filename).type == 'EMPTY':
                    print('found parent ' + filename)
                    obj.parent = scene.objects[filename]

    if option_findmtls:
        for file in file_list:        
            folder = glob.glob(file.rsplit('/',1)[0] + '/*.mtl')
            #print(folder)
            for mtl in folder:
                if not mtl in mat_list:
                    mat_list.append(mtl)
                    
    
    #one last pass to tag the root parent nodes
    for obj in scene.objects[:]:
        if obj.parent is None:
            obj['Root'] = True
            
    #process and spit out logs
    file_list.sort()
    mat_list.sort()
    print("\n")    
    log_text = (bpy.data.texts.get(log_files) or bpy.data.texts.new(log_files))
    
    #if file_list: file_list = file_list.sort()
    for file in file_list:
        file = file.replace(r"/", "\\")
        print(file)
        log_text.write(file + '\n')
    log_text = (bpy.data.texts.get(log_mats) or bpy.data.texts.new(log_mats))
    
    for mat in mat_list:
        mat = mat.replace(r"/", "\\")
        print(mat)
        log_text.write(mat + '\n')
        
    return {'FINISHED'}

def stripPath(path):
    path = path.replace('\\', '/')
    path = path.rsplit('/',1)[1]
    path = path.rsplit('.',1)[0]
    return path

def readMtlfromDAE(path):
    ns = {'': 'http://www.collada.org/2005/11/COLLADASchema'}
    try:
        xml_root = ElementTree.parse(path).getroot()
    except:
        print('Unable to open DAE: ', path)
        return None    
    return xml_root.find('./asset/extra', ns).get('name')
        
                        
class ImportParseXml(Operator, ImportHelper):
    bl_idname = "import_sctools.preimport"  
    bl_label = "Pre-Import SC Prefab"

    # ImportHelper mixin class uses this
    filename_ext = ".xml"

    filter_glob: StringProperty(
        default="*.xml",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    option_brushes: BoolProperty(
        name="Import Brushes",
        description="Import Brushes",
        default=True,
    )

    def execute(self, context):
        return parseXML(self.filepath)


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportSomeData.bl_idname, text="Text Import Operator")


def register():
    bpy.utils.register_class(ImportParseXml)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportParseXml)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.import_sctools.preimport('INVOKE_DEFAULT')

                        
#parseXML(r'X:\SC312\Data\Prefabs\pu\modular\common\hangar\room_construct.xml')


