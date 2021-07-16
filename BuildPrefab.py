import bpy
from xml.etree import cElementTree as ElementTree
from ast import literal_eval as make_tuple
import math
import os.path
from datetime import datetime

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

context = bpy.context
scene = context.scene
import_basedir = r'x:/sc312/data/'
option_brushes = True
option_component = True
option_lights = False
option_spawn = False
option_preconvert = False
option_fixorphans = True
option_import = True


def buildPrefab(context, xml_path):

    xml_root = ElementTree.parse(xml_path).getroot() 

    for element in xml_root:
        root_empty = bpy.data.objects.new("empty", None)
        root_empty.name = element.get("Name") + ".root"
        root_empty['_id'] = element.get("Id")
        scene.collection.objects.link(root_empty)
        writetoLog("Processing " + element.get("Name") + " - Entities: " + str(len(element[0])))
        total_elements = str(len(element[0]))
        # prefab_name = element.get('Name')
        index_elements = 0
        if index_elements > 1: break
        for subelement in element[0]:                    
            index_elements += 1            
            if option_brushes and subelement.get('Type') == 'Brush':
                writetoLog(subelement.get('Type') + ": " + subelement.get('Name'))
                new_assetfilename = import_basedir + subelement.get('Prefab')
                new_assetfilename = new_assetfilename.replace('\\', '/')
                new_assetfilename = new_assetfilename.replace('.cgf', '.dae')
                new_assetfilename = new_assetfilename.replace('.cga', '.dae')
                if subelement.get('Material'): writetoLog(import_basedir + str(subelement.get('Material'))+'.mtl', 'Material')
                new_assets = [obj for obj in scene.objects if obj.get('_id') == new_assetfilename]
                if len(new_assets) == 0:
                    if importAssets(new_assetfilename) is False: continue
                new_asset = getrootParent(bpy.context.selected_objects)
                if new_asset == None: 
                    writetoLog("Root not found for " + new_assetfilename, 'Error')
                    continue
                new_assets = bpy.context.selected_objects
                new_asset.name = subelement.get('Name')                

                setProperty(new_assets, 'Type', subelement.get('Type')) 
                setProperty(new_assets, 'Prefab', subelement.get('Name'))
                setProperty(new_assets, 'Layer', subelement.get('Layer'))  
                setProperty(new_assets, '_id', subelement.get('Id'))

                #new_asset.parent = root_empty
                # new_asset.matrix_parent_inverse.identity()
                if subelement.get('Pos'): new_asset.location = make_tuple(str(subelement.get("Pos")))
                new_asset.rotation_mode = 'QUATERNION'
                if subelement.get('Rotate'): new_asset.rotation_quaternion = make_tuple(subelement.get("Rotate"))
                if subelement.get('Scale'): new_asset.scale = make_tuple(subelement.get("Scale"))
                if element.get('Name'): addtoCollection(element.get('Name'), new_assets)
                # bpy.context.scene.collection.objects.link(new_asset)
            elif option_component and subelement.get('Type') == 'EntityWithComponent':
                writetoLog(subelement.get('Type') + ": " + subelement.get('Name'))
                if subelement[0][0].find('Properties') == 'NoneType': continue
                new_assetfilename = import_basedir + str(subelement[0][0].find('Properties').get('FilePath'))
                new_assetfilename = new_assetfilename.replace('.cgf', '.dae')
                new_assetfilename = new_assetfilename.replace('.cga', '.dae')
                if subelement.get('Material'): writetoLog(import_basedir + str(subelement.get('Material'))+'.mtl', 'Material')
                if importAssets(new_assetfilename) is False: continue
                new_asset = getrootParent(bpy.context.selected_objects)
                new_assets = bpy.context.selected_objects
                new_asset.name = subelement.get('Name')
                setProperty(new_assets, 'Type', subelement.get('Type')) 
                setProperty(new_assets, 'Prefab', subelement.get('Name'))
                setProperty(new_assets, 'Layer', subelement.get('Layer'))  
                setProperty(new_assets, '_id', subelement.get('Id'))               
                #new_asset.parent = root_empty
                # new_asset.matrix_parent_inverse.identity()
                if subelement.get('Pos'): new_asset.location = make_tuple(str(subelement.get("Pos")))
                new_asset.rotation_mode = 'QUATERNION'
                if subelement.get('Rotate'): new_asset.rotation_quaternion = make_tuple(subelement.get("Rotate"))
                if subelement.get('Scale'): new_asset.scale = make_tuple(subelement.get("Scale"))                
                if element.get('Name'): addtoCollection(element.get('Name'), new_assets)                     
                # bpy.context.scene.collection.objects.link(new_asset)                
            elif option_lights and subelement.get('Type') == 'Entity' and subelement.get('EntityClass') == "Light":
                
                writetoLog(subelement.get('Type') + ": " + subelement.get('Name'))
                
                lightType = subelement.findall('./PropertiesDataCore/EntityComponentLight')[0].get('lightType')
                useTemperature = subelement.findall('./PropertiesDataCore/EntityComponentLight')[0].get('useTemperature')
                bulbRadius = subelement.findall('./PropertiesDataCore/EntityComponentLight/sizeParams')[0].get('bulbRadius') or .01
                planeHeight = subelement.findall('./PropertiesDataCore/EntityComponentLight/sizeParams')[0].get('PlaneHeight') or 1
                planeWidth = subelement.findall('./PropertiesDataCore/EntityComponentLight/sizeParams')[0].get('PlaneWidth') or 1
                color_r = subelement.findall('./PropertiesDataCore/EntityComponentLight/defaultState')[0].get('r') or 1
                color_g = subelement.findall('./PropertiesDataCore/EntityComponentLight/defaultState')[0].get('g') or 1
                color_b = subelement.findall('./PropertiesDataCore/EntityComponentLight/defaultState')[0].get('b') or 1
                intensity = subelement.findall('./PropertiesDataCore/EntityComponentLight/defaultState')[0].get('intensity') or 1
                temperature = subelement.findall('./PropertiesDataCore/EntityComponentLight/defaultState')[0].get('temperature') or 1
                texture = subelement.findall('./PropertiesDataCore/EntityComponentLight/projectorParams')[0].get('texture') or False
                fov = subelement.findall('./PropertiesDataCore/EntityComponentLight/projectorParams')[0].get('FOV') or 179
                focusedBeam = subelement.findall('./PropertiesDataCore/EntityComponentLight/projectorParams')[0].get('focusedBeam') or 1
                
                bulbRadius = float(bulbRadius) * .01            
                
                
                # if subelement.find('Properties').get('bActive')=="0": continue
                # if subelement.findall('.//Projector')[0].get('texture_Texture') == ("" or " "): continue
                if lightType == "Projector":
                    # Area lights
                    new_lightdata = (bpy.data.lights.get("Name") or bpy.data.lights.new(name=subelement.get("Name"), type='SPOT'))
                    #new_lightdata.shape = "RECTANGLE"
                    new_lightdata.spot_size = math.radians(float(fov))
                    new_lightdata.spot_blend = float(focusedBeam)
                    #new_lightdata.size = float(planeHeight)
                    #new_lightdata.size_y = float(planeWidth)
                else: 
                    # Point Lights       
                    new_lightdata = (bpy.data.lights.get("Name") or bpy.data.lights.new(name=subelement.get("Name"), type='POINT'))                    
                    #new_lightdata.spot_size = math.radians(float(fov))
                    new_lightdata.shadow_soft_size = float(bulbRadius)
                    #writetoLog("Spot Size " + str(new_lightdata.spot_size))
                    #new_lightdata.spot_blend = float(focusedBeam)
               
                new_lightdata.color = (color_r, color_g, color_b)                     
                new_lightdata.photographer.use_light_temperature = bool(int(useTemperature))
                new_lightdata.photographer.light_temperature = float(temperature)
                new_lightdata.energy = float(intensity)*100                
                new_lightdata.use_nodes = True
                if texture:
                    ies_name = import_basedir + str(texture)
                    new_lightdata['Texture'] = ies_name
                    ies_group = new_lightdata.node_tree.nodes.new(type="ShaderNodeGroup")
                    ies_group.node_tree = createLightTexture(ies_name)
                    ies_group.location.x -= 200
                    new_lightdata.node_tree.links.new(ies_group.outputs[0], new_lightdata.node_tree.nodes['Emission'].inputs[0])
                new_lightobject = bpy.data.objects.new(name=subelement.get("Name"), object_data=new_lightdata)
                new_lightobject['Type'] = subelement.get('Type')
                new_lightobject['_id'] = subelement.get('Id')
                #new_lightobject.parent = root_empty
                new_lightobject.matrix_parent_inverse.identity()
                new_lightobject.location = make_tuple(subelement.get("Pos"))
                if subelement.get("Rotate"):
                    new_lightobject.rotation_mode = 'QUATERNION'
                    new_lightobject.rotation_quaternion = makeQuatTuple(subelement.get("Rotate"))
                    new_lightobject.rotation_mode = 'XYZ'
                    new_lightobject.rotation_euler[0] += 1.5708
                    new_lightobject.rotation_mode = 'QUATERNION'                  
                new_lightobject_radius = .1 
                new_lightobject.scale = (new_lightobject_radius, new_lightobject_radius, new_lightobject_radius * -1)
                new_lightobject.data.shadow_soft_size= float(bulbRadius)
                if subelement.get('Layer'): addtoCollection(element.get('Name'), new_lightobject)  
                bpy.context.scene.collection.objects.link(new_lightobject)
                if element.get('Name'): addtoCollection(element.get('Name'), new_lightobject)
            elif option_spawn and subelement.get('Type') == 'Entity' and subelement.get('EntityClass') == 'DynamicHangarVehicleSpawn':
                #writetoLog(subelement.get('Type') + ": " + subelement.get('Name'))
                new_empty = bpy.data.objects.new("empty", None)
                new_empty.name = subelement.get('Name')
                new_asset['Type'] = subelement.get('Type')
                new_asset['_id'] = subelement.get('Id')
                #new_empty.parent = root_empty
                new_empty.location = make_tuple(subelement.get("Pos"))
                new_empty.rotation_mode = 'QUATERNION'
                new_empty.rotation_quaternion = makeQuatTuple(subelement.get("Rotate"))
                bpy.context.scene.collection.objects.link(new_empty)
                new_empty.empty_display_size = 1
                new_empty.empty_display_type = 'PLAIN_AXES'
            
    return {'FINISHED'}


def addtoCollection(name, objs):
    
    name = name[:61] #shorten it to max Blender collection name length
    
    if bpy.data.collections.find(name) != -1:
        new_collection = bpy.data.collections[name]
        new_empty = bpy.data.objects.new("empty", None)
    else: 
        new_collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(new_collection)
    
    viewlayer = context.view_layer.layer_collection.children.get(name)
    if viewlayer: context.view_layer.active_layer_collection = viewlayer   
        
    new_empty = (bpy.data.objects.get(name) or bpy.data.objects.new("empty", None))
    new_empty.name = name
    try:
        bpy.data.collections[name].objects.link(new_empty)
    except:
        pass
    
        
    if type(objs) is list:
        for obj in objs:
            if bpy.data.collections[name].objects.find(obj.name) == -1: bpy.data.collections[name].objects.link(obj)
            #bpy.context.scene.collection.children.unlink(obj)
            if obj.parent is None: obj.parent = new_empty                    
    else: 
        if bpy.data.collections[name].objects.find(objs.name) == -1: bpy.data.collections[name].objects.link(objs)
        #bpy.context.scene.collection.children.unlink(objs)
        if objs.parent is None: objs.parent = new_empty
        
def setProperty(objs, name, value):
    if type(objs) is list:
        for obj in objs:
            obj[name] = value
    else: 
        objs[name] = value
        
def getrootParent(objs):
    for obj in objs:
        if obj.get('Root') != None: return obj
    return None    
           

def importAssets(new_assetfilename):
    new_assetfilename = new_assetfilename.lower()
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.context.selected_objects: obj.select_set(False)
    #writetoLog("Searching for: " + new_assetfilename)
    new_assets = [obj for obj in scene.objects if obj.get('Filename') == new_assetfilename]
    # new_assets = []
   
    if not new_assets:
        if option_import:
            if os.path.isfile(new_assetfilename) is False: 
                writetoLog('Not found ' + new_assetfilename, 'Error')
                new_empty = bpy.data.objects.new("empty", None)
                new_empty.empty_display_type = 'CUBE'
                return False
            try:
                import_return = bpy.ops.wm.collada_import(filepath=new_assetfilename)        
            except:
                writetoLog('Import Error ' + new_assetfilename, 'Error')
                new_empty = bpy.data.objects.new("empty", None)
                new_empty.empty_display_type = 'CUBE'
                new_empty['Filename'] = new_assetfilename
                return False
        
        new_assets = bpy.context.selected_objects
        
        if len(new_assets) == 0: 
            writetoLog('Nothing created ' + new_assetfilename)    
            return False
        else:
            writetoLog('Imported ' + str(len(new_assets)) + ' new objects')

        new_assets_parent = [obj for obj in new_assets if obj.type=='EMPTY' and '$' not in obj.name]
        

        for obj in new_assets_parent:
            writetoLog('Possible parent ' + obj.name)    
        for obj in new_assets:
            writetoLog('Imported ' + str(obj.type) + ' ' + str(obj.name))
            obj['Filename']= str(new_assetfilename)
            if option_fixorphans and '.Merged' in obj.name:
                writetoLog('Fixing ' + obj.name)
                obj.name = stripPath(new_assetfilename) + ".Merged"
                writetoLog('Fixed ' + obj.name)
                try:
                    obj.parent = new_assets_parent[0]
                    writetoLog('Reparented ' + obj.name + ' to ' + new_assets_parent[0].name)
                except:
                    writetoLog('Unable to reparent ' + obj.name)         
        return True        
    else:            
            #writetoLog('Duplicating ' + new_assetfilename)
            duped_assetnames = {}
            #bpy.ops.object.select_all(action='DESELECT')            
            for obj in new_assets:
                duped_asset = obj.copy()
                bpy.context.scene.collection.objects.link(duped_asset)
                duped_asset['Filename'] = ''
                #writetoLog('Duplicated ' + duped_asset.type + ' ' + obj.name + ' -> ' + duped_asset.name)
                duped_assetnames[obj.name] = duped_asset.name
                duped_asset.select_set(True)                
            new_assets = bpy.context.selected_objects
            for obj in new_assets:
                if obj.parent:                    
                    obj.parent = getrootParent(new_assets)
                    if obj.parent == None:
                        writetoLog('Unable to reparent ' + obj.name + ' to asset ' + new_assetfilename) 
                        return False
                    #writetoLog('Reparented ' + obj.name + ' to ' + obj.parent.name)
                                                       
    return True

def createLightTexture(texture):
    texture = texture.replace('.dds', '.tif')
    texture_name = stripPath(texture)    
    writetoLog('IES: ' + texture) 
        
    if bpy.data.node_groups.get(texture_name): return bpy.data.node_groups.get(texture_name)
    
    new_node = bpy.data.node_groups.new(texture_name, "ShaderNodeTree")
    new_node_output = new_node.nodes.new('NodeGroupOutput')
    new_node.outputs.new("NodeSocketColor", "Color")
    new_node_output.location = (700,0)
    new_node_texture = new_node.nodes.new('ShaderNodeTexImage')
    new_node_texture.location = (400,0)
    new_node_texture.location = (400,0)
    try:
        new_node_texture.image = (bpy.data.images.get(texture_name) or bpy.data.images.load(texture))
        new_node_texture.image.colorspace_settings.name = 'Non-Color'
    except:
        writetoLog('IES not found: ' + texture, 'Error')    
    new_node_mapping = new_node.nodes.new('ShaderNodeMapping')
    new_node_mapping.location = (200,0)
    new_node_mapping.inputs['Location'].default_value = (0.5, 0.5, 0)
    new_node_mapping.inputs['Scale'].default_value = (0.5, 0.5, 0)
    new_node_texcoord = new_node.nodes.new('ShaderNodeTexCoord')
    new_node_texcoord.location = (0,0)
    new_node.links.new(new_node_texture.outputs['Color'], new_node_output.inputs['Color'])
    new_node.links.new(new_node_mapping.outputs['Vector'], new_node_texture.inputs['Vector'])
    new_node.links.new(new_node_texcoord.outputs['Normal'], new_node_mapping.inputs['Vector'])
    
    return new_node


            
def stripPath(path):
    path = path.replace('\\', '/')
    path = path.rsplit('/',1)[1]
    path = path.rsplit('.',1)[0]
    return path 

def makeTuple(input):
    output = input.rsplit(',')
    for i in range(0, len(output)): 
        output[i] = float(str(output[i])[0:6])
    return output

def makeQuatTuple(input):
    output = input.rsplit(',')
    for i in range(0, len(output)): 
        output[i] = float(output[i])
        #output[3] *= -1    
    output = [output[3], output[2], output[1], output[0]] #ZYXW to WXYZ 
    return output
        
def writetoLog(log_text, log_name = 'Output'):
    log_file = (bpy.data.texts.get(log_name) or bpy.data.texts.new(log_name))
    log_file.write('[' + str(datetime.now()) + '] ' + log_text + '\n')
    print('[' + str(datetime.now()) + '] ' + log_text)


class ImportSCPrefab(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "sctools.buildprefab"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import SC Prefab"

    # ImportHelper mixin class uses this
    filename_ext = ".xml"

    filter_glob: StringProperty(
        default="*.xml",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    option_brushes: BoolProperty(
        name="option_brushes",
        description="Import Brushes",
        default=True,
    )
    option_component: BoolProperty(
        name="option_component",
        description="Components",
        default=True,
    )
    option_lights: BoolProperty(
        name="option_lights",
        description="Lights",
        default=True,
    )
    option_spawn: BoolProperty(
        name="option_spawn",
        description="Spawn Points",
        default=True,
    )
    option_import: BoolProperty(
        name="option_import",
        description="Import Assets as needed",
        default=True,
    )

    def execute(self, context):
        return buildPrefab(context, self.filepath)


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportSCPrefab.bl_idname, text="Import SC Prefab")


def register():
    bpy.utils.register_class(ImportSCPrefab)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportSCPrefab)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.sctools.buildprefab('INVOKE_DEFAULT')

#buildPrefab(r'X:\SC312\Data\Prefabs\pu\modular\common\hangar\room_construct.xml')

