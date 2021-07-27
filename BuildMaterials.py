# -*- coding: utf-8 -*-
import bpy
from xml.etree import cElementTree as ElementTree
from ast import literal_eval as make_tuple
import os
from datetime import datetime
importBaseDir = r'D:/SC313/Data/'

def read_MTL_data(context, filepath, use_some_setting):
    print("Importing from " + filepath)
    createMaterialsFromMTL(filepath)
    print("Finished")

    return {'FINISHED'}

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, CollectionProperty
from bpy.types import Operator, OperatorFileListElement


class ImportMTL(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "import_test.some_data"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import SC Materials"
    
    files = CollectionProperty(
            name="File Path",
            type=OperatorFileListElement,
            )
    directory = StringProperty(
            subtype='DIR_PATH',
            )
            
    # ImportHelper mixin class uses this
    filename_ext = ".mtl"

    filter_glob: StringProperty(
        default="*.mtl",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    importBaseDir: StringProperty(
        default=importBaseDir,
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    use_setting: BoolProperty(
        name="Overwrite Materials",
        description="Overwrite materials that have the same name (UNIMPLMENTED)",
        default=True,    
    )


    def execute(self, context):
        #for file in self.files:
        #    filepath = os.path.join(self.directory, file.name)
        #    return read_MTL_data(context, self.filepath, self.use_setting)
        #filepath = os.path.join(self.directory, self.files.name)
        return read_MTL_data(context, self.filepath, self.use_setting)


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportMTL.bl_idname, text="Import SC Materials")


def register():
    bpy.utils.register_class(ImportMTL)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportMTL)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


def createMaterialsFromMTL(xmlPath):
    try:
        parser = ElementTree.XMLParser(encoding='utf-8')
        xmlRoot = ElementTree.parse(xmlPath, parser=parser).iter('Material')
        #xmlRoot = ElementTree.parse(xmlPath).iter('Material')
    except Exception as e:
        writetoLog("XML not found: " + xmlPath, 'Error')
        writetoLog("Error: " + str(e), 'Error')
        #print('XML can\'t be opened')
        return False
    
    xmlPath = xmlPath.replace('\\', '/')
    xmlName = xmlPath.rsplit('/',1)[1]
    xmlName = xmlName.rsplit('.',1)[0] 
    writetoLog("Opening: " + xmlPath)
        
    for element in xmlRoot:
        if element.get('Name') == None: element.set('Name', xmlName)         
        writetoLog("Material Name: " + str(element.get('Name')))
        writetoLog("Shader type: " + str(element.get('Shader')))
        mtlvalues = element.attrib       
                
        for subelement in element:
            #print(" " + subelement.tag)
            mtlvalues[subelement.tag] = subelement
            for key, value in subelement.attrib.items():
                continue
                #print("  " + key + ": " + value)
            #for texture in subelement.getchildren():
                #print("  Texture: ")
                #print(texture.attrib)
        if bpy.data.materials.get('Name') and use_setting == False:
            if bpy.data.materials['Name']['Filename']:
                writetoLog("Skipping")
                continue
            
        if element.get('Name') in ("proxy", "Proxy"):
            mat = createNoSurface(**mtlvalues)              
        elif element.get('Shader') in ("Ilum", "Illum", "MeshDecal"): 
            mat = createIlumSurface(**mtlvalues)
        elif element.get('Shader') == "HardSurface":
            mat = createHardSurface(**mtlvalues)         
        elif element.get('Shader') in ("Glass", "GlassPBR"):
            mat = createGlassSurface(**mtlvalues)
        elif element.get('Shader') == "LayerBlend":
            mat = createLayerBlendSurface(**mtlvalues)
        elif element.get('Shader') == "Layer":
            mat = createLayerNode(**mtlvalues)                      
        elif element.get('Shader') == "NoDraw":
            mat = createNoSurface(**mtlvalues)
        else:
            writetoLog("Shader type not found " + str(element.get('Shader')))
            #mat = createUnknownSurface(**mtlvalues)
            continue        
        if mat != None:
            mat['Filename'] = xmlPath
            print('Imported material ' + str(element.get('Name')))       
    return True

    
def createIlumSurface(**mtl):
    writetoLog(mtl["Shader"] + " - " + mtl["SurfaceType"])
    mat = (bpy.data.materials.get(mtl["Name"]) or bpy.data.materials.new(mtl["Name"]))
    
    setViewport(mat, mtl)
        
    #Shader 
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    shaderout = nodes.new(type="ShaderNodeOutputMaterial")
    shadergroup = nodes.new(type="ShaderNodeGroup")
    writeAttribs(mat, mtl, "PublicParams")
    
    if "pom" in mtl["Name"]:
        shadergroup.node_tree = bpy.data.node_groups['_Illum.pom']
        setViewport(mat, mtl, True)
    elif "decal" in mtl["Name"]:
        shadergroup.node_tree = bpy.data.node_groups['_Illum.decal']
        setViewport(mat, mtl, True)
    elif "glow" in mtl["Name"]:
        shadergroup.node_tree = bpy.data.node_groups['_Illum.emit']        
    else:
        shadergroup.node_tree = bpy.data.node_groups['_Illum']
    
    mat.node_tree.links.new(shadergroup.outputs['BSDF'], shaderout.inputs['Surface'])
    mat.node_tree.links.new(shadergroup.outputs['Displacement'], shaderout.inputs['Displacement'])
    
    if "pom" in mtl["Name"]:
        shadergroup.inputs['Base Color'].default_value = (0.5,0.5,0.5,1)
        shadergroup.inputs['n Strength'].default_value = .1
    else:
        shadergroup.inputs['Base Color'].default_value = mat.diffuse_color
    
    shadergroup.inputs['ddna Alpha'].default_value =  mat.roughness    
    shadergroup.inputs['spec Color'].default_value = mat.specular_color[0]
    
    shaderout.location.x += 200
    
    loadTextures(mtl["Textures"], nodes, mat, shadergroup) 

    
    if not mtl.get("MatLayers"): return mat

    for submat in mtl["MatLayers"]:
        if "WearLayer" in submat.get("Name"): continue
        path = importBaseDir + submat.get("Path")
        writetoLog(stripPath(path))
        newbasegroup=nodes.new("ShaderNodeGroup")       
        if createMaterialsFromMTL(path) == False:
            writetoLog("MTL not found: " + str(path),"Error")
            continue 
        newbasegroup.node_tree = bpy.data.node_groups[stripPath(path)] 
        newbasegroup.name = submat.get("Name")
        #newbasegroup.node_tree.label = submat.get("Name")
        newbasegroup.inputs['tint Color'].default_value = make_tuple(str(submat.get("TintColor")) + ",1")
        newbasegroup.inputs['UV Scale'].default_value = [float(submat.get("UVTiling")), float(submat.get("UVTiling")), float(submat.get("UVTiling"))]
        newbasegroup.location.x = -600
        newbasegroup.location.y += y
        y -= 260
        mat.node_tree.links.new(newbasegroup.outputs['diff Color'], shadergroup.inputs[newbasegroup.name + ' ' + 'diff Color'])
        mat.node_tree.links.new(newbasegroup.outputs['diff Alpha'], shadergroup.inputs[newbasegroup.name + ' ' + 'diff Alpha'])
        mat.node_tree.links.new(newbasegroup.outputs['ddna Color'], shadergroup.inputs[newbasegroup.name + ' ' + 'ddna Color'])
        mat.node_tree.links.new(newbasegroup.outputs['ddna Alpha'], shadergroup.inputs[newbasegroup.name + ' ' + 'ddna Alpha'])
        mat.node_tree.links.new(newbasegroup.outputs['spec Color'], shadergroup.inputs[newbasegroup.name + ' ' + 'spec Color'])
        mat.node_tree.links.new(newbasegroup.outputs['disp Color'], shadergroup.inputs[newbasegroup.name + ' ' + 'disp Alpha'])
        mat.node_tree.links.new(newbasegroup.outputs['metal Color'], shadergroup.inputs[newbasegroup.name + ' ' + 'metal Alpha'])
        mat.node_tree.links.new(newbasegroup.outputs['blend Color'], shadergroup.inputs[newbasegroup.name + ' ' + 'blend Alpha'])                            
    return mat


def createHardSurface(**mtl):
    writetoLog("Material: " + mtl["Name"])
    mat = (bpy.data.materials.get(mtl["Name"]) or bpy.data.materials.new(mtl["Name"]))
    
    setViewport(mat, mtl)
    
    #Shader 
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    shaderout = nodes.new(type="ShaderNodeOutputMaterial")
    shadergroup = nodes.new(type="ShaderNodeGroup")
    shadergroup.node_tree = bpy.data.node_groups['_HardSurface']
    mat.node_tree.links.new(shadergroup.outputs['BSDF'], shaderout.inputs['Surface'])
    mat.node_tree.links.new(shadergroup.outputs['Displacement'], shaderout.inputs['Displacement'])
    shadergroup.inputs['Base Color'].default_value = mat.diffuse_color
    shadergroup.inputs['Primary ddna Alpha'].default_value =  mat.roughness
    shadergroup.inputs['Metallic'].default_value = 0
    shadergroup.inputs['Anisotropic'].default_value = .5
    shadergroup.inputs['Emission'].default_value = make_tuple(mtl["Emissive"] + ",1")
        
    
    shaderout.location.x += 200
        
    writeAttribs(mat, mtl, "PublicParams")
    loadTextures(mtl["Textures"], nodes, mat, shadergroup)    
    
    if not mtl.get("MatLayers"): return mat

    y=-300
    
    for submat in mtl["MatLayers"]:
        #if "WearLayer" in submat.get("Name"): continue
        path = importBaseDir + submat.get("Path")
        writetoLog("MTL: " + stripPath(path))
        newbasegroup = nodes.new("ShaderNodeGroup")       
        if createMaterialsFromMTL(path) == False:
            writetoLog("MTL not found: " + str(path),"Error")
            continue 
        newbasegroup.node_tree = bpy.data.node_groups[stripPath(path)] 
        if 'Wear' in submat.get("Name"):
            newbasegroup.name = 'Secondary'
        else:
            newbasegroup.name = submat.get("Name")
  
        #newbasegroup.node_tree.label = submat.get("Name")
        newbasegroup.inputs['tint Color'].default_value = make_tuple(str(submat.get("TintColor")) + ",1")
        newbasegroup.inputs['UV Scale'].default_value = [float(submat.get("UVTiling")), float(submat.get("UVTiling")), float(submat.get("UVTiling"))]
        newbasegroup.location.x = -600
        newbasegroup.location.y += y
        y -= 300
        mat.node_tree.links.new(newbasegroup.outputs['diff Color'], shadergroup.inputs[newbasegroup.name + ' ' + 'diff Color'])
        mat.node_tree.links.new(newbasegroup.outputs['diff Alpha'], shadergroup.inputs[newbasegroup.name + ' ' + 'diff Alpha'])
        mat.node_tree.links.new(newbasegroup.outputs['ddna Color'], shadergroup.inputs[newbasegroup.name + ' ' + 'ddna Color'])
        mat.node_tree.links.new(newbasegroup.outputs['ddna Alpha'], shadergroup.inputs[newbasegroup.name + ' ' + 'ddna Alpha'])
        mat.node_tree.links.new(newbasegroup.outputs['spec Color'], shadergroup.inputs[newbasegroup.name + ' ' + 'spec Color'])
        mat.node_tree.links.new(newbasegroup.outputs['disp Color'], shadergroup.inputs[newbasegroup.name + ' ' + 'disp Color'])
        mat.node_tree.links.new(newbasegroup.outputs['blend Color'], shadergroup.inputs[newbasegroup.name + ' ' + 'blend Color'])              
    
    return mat


def createGlassSurface(**mtl):
    writetoLog("Material: " + mtl["Name"])
    mat = (bpy.data.materials.get(mtl["Name"]) or bpy.data.materials.new(mtl["Name"]))
    
    #Viewport material values
    setViewport(mat, mtl, True)
    
    #Shader 
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    shaderout = nodes.new(type="ShaderNodeOutputMaterial")
    shadergroup = nodes.new(type="ShaderNodeGroup")
    shadergroup.node_tree = bpy.data.node_groups['_Glass']
    mat.node_tree.links.new(shadergroup.outputs['BSDF'], shaderout.inputs['Surface'])
    mat.node_tree.links.new(shadergroup.outputs['Displacement'], shaderout.inputs['Displacement'])
    shadergroup.inputs['Base Color'].default_value = mat.diffuse_color
    shadergroup.inputs['ddna Alpha'].default_value =  mat.roughness
    shadergroup.inputs['spec Color'].default_value = mat.specular_color[0]
    shaderout.location.x += 200
        
    loadTextures(mtl["Textures"], nodes, mat, shadergroup)        
    
    return mat

    
def createLayerBlendSurface(**mtl):
    writetoLog("Material: " + mtl["Name"])
    mat = (bpy.data.materials.get(mtl["Name"]) or bpy.data.materials.new(mtl["Name"]))
    
    #Viewport material values
    setViewport(mat, mtl)
    
    #Shader 
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    shaderout = nodes.new(type="ShaderNodeOutputMaterial")
    shadergroup = nodes.new(type="ShaderNodeGroup")
    shadergroup.node_tree = bpy.data.node_groups['_LayerBlend']
    mat.node_tree.links.new(shadergroup.outputs['BSDF'], shaderout.inputs['Surface'])
    mat.node_tree.links.new(shadergroup.outputs['Displacement'], shaderout.inputs['Displacement'])
    shadergroup.inputs['Base Color'].default_value = mat.diffuse_color
    shadergroup.inputs['ddna Alpha'].default_value =  mat.roughness
    shaderout.location.x += 200
    
    #loadMaterials(mtl["MatLayers"])

    loadTextures(mtl["Textures"], nodes, mat, shadergroup)       
    
    y=-300
    
    

    mats = (mtl.get("MatLayers") or mtl.get("MatReferences"))
    
    if mats == None: return
        
    for submat in mats:
        #if submat.get("Name") in "WearLayer": continue
        path = str(submat.get("Path") or submat.get("File"))
        path = importBaseDir + path
        writetoLog(stripPath(path))
        newbasegroup=nodes.new("ShaderNodeGroup")       
        if createMaterialsFromMTL(path) == False:
            writetoLog("MTL not found: " + str(path),"Error")
            continue 
        newbasegroup.node_tree = bpy.data.node_groups[stripPath(path)] 
        if submat.get("Name"):
            newbasegroup.name = submat.get("Name")
        elif submat.get("Slot"):
            newbasegroup.name = 'BaseLayer' + str(int(submat.get("Slot"))+1)
        else:
            newbasegroup.name = 'Unknown'
        #newbasegroup.node_tree.label = submat.get("Name")
        if submat.get("TintColor"):
            newbasegroup.inputs['tint Color'].default_value = make_tuple(str(submat.get("TintColor")) + ",1")
        if submat.get("UVTiling"):            
            newbasegroup.inputs['UV Scale'].default_value = [float(submat.get("UVTiling")), float(submat.get("UVTiling")), float(submat.get("UVTiling"))]
                
        newbasegroup.location.x = -600
        newbasegroup.location.y += y
        y -= 260
        try:    
            mat.node_tree.links.new(newbasegroup.outputs['diff Color'], shadergroup.inputs[newbasegroup.name + ' ' + 'diff Color'])
            mat.node_tree.links.new(newbasegroup.outputs['diff Alpha'], shadergroup.inputs[newbasegroup.name + ' ' + 'diff Alpha'])            
            mat.node_tree.links.new(newbasegroup.outputs['ddna Color'], shadergroup.inputs[newbasegroup.name + ' ' + 'ddna Color'])
            mat.node_tree.links.new(newbasegroup.outputs['ddna Alpha'], shadergroup.inputs[newbasegroup.name + ' ' + 'ddna Alpha'])
            mat.node_tree.links.new(newbasegroup.outputs['spec Color'], shadergroup.inputs[newbasegroup.name + ' ' + 'spec Color'])
            mat.node_tree.links.new(newbasegroup.outputs['disp Color'], shadergroup.inputs[newbasegroup.name + ' ' + 'disp Color'])
            mat.node_tree.links.new(newbasegroup.outputs['blend Color'], shadergroup.inputs[newbasegroup.name + ' ' + 'blend Color'])
            mat.node_tree.links.new(newbasegroup.outputs['metal Color'], shadergroup.inputs[newbasegroup.name + ' ' + 'metal Color'])
        except:
            writetoLog("Unable to link layer " + newbasegroup.name)                    
    return mat


def createLayerNode(**mtl):
    writetoLog("Layer node: " + str(mtl["Name"]))    
    if bpy.data.node_groups.get(mtl["Name"]): return bpy.data.node_groups.get(mtl["Name"])
    mat = (bpy.data.node_groups.get(mtl["Name"]) or bpy.data.node_groups['_MaterialLayer'].copy())
    mat.name = mtl["Name"]
    nodes = mat.nodes
    loadTextures(mtl["Textures"], nodes, mat, nodes['Material Output'])
    #manually connect everything for now
    mapnodeout = mat.nodes['Mapping'].outputs['Vector']
    for node in mat.nodes:
        if node.type == 'TEX_IMAGE':
            imagenodein = node.inputs['Vector']
            imagenodecolorout = node.outputs['Color']
            imagenodealphaout = node.outputs['Alpha']
            mat.links.new(imagenodein, mapnodeout)               
            if node.name in ['TexSlot12', 'Blendmap']:
                mat.links.new(imagenodecolorout, mat.nodes['Material Output'].inputs['blend Color'])
            elif node.name in ['TexSlot1', '_diff']:
                mat.links.new(imagenodecolorout, mat.nodes['Tint'].inputs['diff Color'])
                mat.links.new(imagenodealphaout, mat.nodes['Tint'].inputs['diff Alpha'])
            elif node.name in ['TexSlot2', '_ddna']:
                mat.links.new(imagenodecolorout, mat.nodes['Material Output'].inputs['ddna Color'])
                mat.links.new(imagenodealphaout, mat.nodes['Material Output'].inputs['ddna Alpha'])
            elif node.name in ['TexSlot4', '_spec']:
                mat.links.new(imagenodecolorout, mat.nodes['Material Output'].inputs['spec Color'])
            elif node.name in ['TexSlot8', 'Heightmap']:
                mat.links.new(imagenodecolorout, mat.nodes['Material Output'].inputs['disp Color'])                               
                
    mat['Filename'] = str(mtl['Name']) 
    return mat


def createNoSurface(**mtl):
    writetoLog("Material: " + mtl["Name"])
    mat = (bpy.data.materials.get(mtl["Name"]) or bpy.data.materials.new(mtl["Name"]))
    #Viewport
    mat.blend_method = 'CLIP'
    mat.shadow_method = 'NONE'
    #Shader 
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    shaderout = nodes.new(type="ShaderNodeOutputMaterial")
    shadernode = nodes.new('ShaderNodeBsdfTransparent')
    mat.node_tree.links.new(shadernode.outputs['BSDF'], shaderout.inputs['Surface'])
    return


def createUnknownSurface(**mtl):
    writetoLog("Material: " + mtl["Name"])
    mat = (bpy.data.materials.get(mtl["Name"]) or bpy.data.materials.new(mtl["Name"]))
    
    #Viewport material values
    setViewport(mat, mtl)
    
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    shaderout = nodes.new(type="ShaderNodeOutputMaterial")
    shadergroup = nodes.new(type="ShaderNodeGroup")
    shadergroup.node_tree = (bpy.data.node_groups['_'+element.get('Shader')] or bpy.data.node_groups.new('_'+element.get('Shader')))

    return mat

def createAttribNode(mat, attrs, name):
    return

def loadTextures(textures, nodes, mat, shadergroup = None):
    imglist = []
    y = 0
    #writetoLog("Count of textures: " + str(len(textures)))    
    for tex in textures:        
        writetoLog("Texture" + str(tex.attrib) + " " + tex.get("File"))
        path = importBaseDir + tex.get("File")
        path.replace('.dds', '.tif')
        try:
            img = (bpy.data.images.get(tex.get("File")) or bpy.data.images.load(path))
        except:
            writetoLog("Texture not found: " + path, "Error")
            writetoList(path, "Missing Textures")
            continue        
        if 'diff' in img.name:
            img.colorspace_settings.name = 'sRGB'
        else:
            img.colorspace_settings.name = 'sRGB'

        img.alpha_mode = 'PREMUL'
        texnode = (nodes.get(img.name) or nodes.new(type='ShaderNodeTexImage'))
        texnode.image = img
        texnode.label = img.name
        texnode.name = tex.get("Map")
        
        texnode.location.x -= 300
        texnode.location.y = y
        y -= 330        
        
        if list(tex):
            texmod = tex[0]
            writetoLog("Texture mod found", 'Debug')
            mapnode = nodes.new(type = 'ShaderNodeMapping')
            if (texmod.get('TileU') and texmod.get('TileV')):
                mapnode.inputs['Scale'].default_value = (float(texmod.get('TileU')), float(texmod.get('TileV')), 1) 
                if mapnode.inputs['Scale'].default_value == [0,0,1]: mapnode.inputs['Scale'].default_value = [1,1,1]
                try: 
                    mat.node_tree.links.new(mapnode.outputs['Vector'], texnode.inputs['Vector'])
                except:
                    pass                       
            mapnode.location = texnode.location
            mapnode.location.x -= 300
            #mat.node_tree.links.new(mapnode.outputs['Vector'], texnode.inputs['Vector'])

        if hasattr(mat, 'node_tree') == False: 
            writetoLog("Shader node tree doesn't exist")
            continue 
                
                
        #link everything up
        if tex.get("Map") in ['TexSlot1', 'Diffuse']:
            texnode.image.colorspace_settings.name = 'sRGB'
            try:            
                mat.node_tree.links.new(texnode.outputs['Color'], shadergroup.inputs['diff Color'])
                mat.node_tree.links.new(texnode.outputs['Alpha'], shadergroup.inputs['diff Alpha'])
            except:
                try:
                    mat.node_tree.links.new(texnode.outputs['Color'], shadergroup.inputs['Primary diff Color'])
                    mat.node_tree.links.new(texnode.outputs['Alpha'], shadergroup.inputs['Primary diff Alpha'])
                except:
                    writetoLog("Failed to link Diffuse Map")
        elif tex.get("Map") in ['TexSlot2', 'Bumpmap']:                  
            try:                  
                mat.node_tree.links.new(texnode.outputs['Color'], shadergroup.inputs['ddna Color'])
                #mat.node_tree.links.new(texnode.outputs['Alpha'], shadergroup.inputs['ddna Alpha'])
            except:
                mat.node_tree.links.new(texnode.outputs['Color'], shadergroup.inputs['Primary ddna Color'])
                continue
        elif tex.get("Map") in ['TexSlot3']:
            try:                  
                #mat.node_tree.links.new(texnode.outputs['Color'], shadergroup.inputs['ddna Color'])
                mat.node_tree.links.new(texnode.outputs['Alpha'], shadergroup.inputs['ddna Alpha'])
            except:
                try:
                    mat.node_tree.links.new(texnode.outputs['Color'], shadergroup.inputs['Primary ddna Color'])
                    mat.node_tree.links.new(texnode.outputs['Alpha'], shadergroup.inputs['Primary ddna Alpha'])                
                except:
                    writetoLog("Failed to link DDNA Map")
        elif tex.get("Map") in ['TexSlot4', 'Specular']:
            mat.node_tree.links.new(texnode.outputs['Color'], shadergroup.inputs['spec Color'])
        elif tex.get("Map") in ['TexSlot6']:
            try:
                mat.node_tree.links.new(texnode.outputs['Color'], shadergroup.inputs['detail Color'])
                mat.node_tree.links.new(texnode.outputs['Alpha'], shadergroup.inputs['detail Alpha'])
            except:
                writetoLog("Failed to link detail Map")
                continue    
        elif tex.get("Map") in ['TexSlot8', 'Heightmap']:
            try:
                mat.node_tree.links.new(texnode.outputs['Color'], shadergroup.inputs['disp Color'])
            except:
                pass    
        elif tex.get("Map") in ['TexSlot9', 'Decalmap']:
            try:
                mat.node_tree.links.new(texnode.outputs['Color'], shadergroup.inputs['decal Color'])
                mat.node_tree.links.new(texnode.outputs['Alpha'], shadergroup.inputs['decal Alpha'])
            except:
                writetoLog("Failed to link Decal Map")
                continue
        elif tex.get("Map") in ['TexSlot11', 'WDA']:
            try:
                mat.node_tree.links.new(texnode.outputs['Color'], shadergroup.inputs['wda Color'])
                mat.node_tree.links.new(texnode.outputs['Alpha'], shadergroup.inputs['wda Alpha'])
            except:
                writetoLog("Failed to link WDA Map")
                continue
        elif tex.get("Map") in ['TexSlot12', 'Blendmap']:
            try:
                mat.node_tree.links.new(texnode.outputs['Color'], shadergroup.inputs['blend Color'])
            except:
                writetoLog("Failed to link Blend Map")
                continue
        elif tex.get("Map") in ['TexSlot13', 'Blendmap']:
            try:
                #mat.node_tree.links.new(texnode.outputs['Color'], shadergroup.inputs['detail Color'])
                #mat.node_tree.links.new(texnode.outputs['Alpha'], shadergroup.inputs['detail Alpha'])
                pass
            except:
                writetoLog("Failed to link detail Map")
                continue     
            
    return mat

    
def loadMaterials(materials):        
        for mat in materials:
            path = importBaseDir + mat.get("Path")
            writetoLog("Path: " + path)            
            createMaterialsFromMTL(path)


def setViewport(mat, mtl, trans=False):
    #Viewport material values
    mat.diffuse_color = make_tuple(mtl["Diffuse"] + ",1")    
    #mat.specular_color = make_tuple(mtl["Specular"],.5)
    #mat.roughness = 1-(float(mtl["Shininess"].5)/255)
    if trans:
        mat.blend_method = 'BLEND'
        mat.shadow_method = 'NONE'
        mat.show_transparent_back = True
        mat.cycles.use_transparent_shadow = True
        mat.use_screen_refraction = True        
        mat.refraction_depth = .0001
    else:
        mat.blend_method = 'OPAQUE'
        mat.shadow_method = 'CLIP'
        mat.cycles.use_transparent_shadow = False
        mat.show_transparent_back = False
    return

        

def writeAttribs(mat, mtl, attr):
    #if not mtl.get(attr): return False
    for name, value in mtl[attr].attrib.items():
        writetoLog(name + " " + value, 'Debug')
        mat[name] = value
        if mat.node_tree.nodes['Group'].inputs.get(name):
            mat.node_tree.nodes['Group'].inputs[name].default_value = float(value)
    return                             

def makeTuple(input):
    if input == None: return False
    output = input.rsplit(',')
    for i in range(0, len(output)): 
        output[i] = float(str(output[i])[0:6])
    return output


def stripPath(path):
    path = path.replace('\\', '/')
    path = path.rsplit('/',1)[1]
    path = path.rsplit('.',1)[0]
    return path 


def writetoLog(log_text, log_name = 'Output'):
    log_file = (bpy.data.texts.get(log_name) or bpy.data.texts.new(log_name))
    log_file.write('[' + str(datetime.now()) + '] ' + log_text + '\n')
    #print('[' + str(datetime.now()) + '] ' + log_text + '\n')


def writetoList(log_text, log_name = 'Output'):
    log_file = (bpy.data.texts.get(log_name) or bpy.data.texts.new(log_name))
    if log_text in log_file.as_string():
        return
    log_file.write(log_text)
    log_file.write('\n')
    
    #a = split('\n', log_file.as_string())
    #a.sort()
    #log_file.clear()
    #log_file.write(join('\n', a))
    


if __name__ == "__main__":
    #unregister()
    register()
    
    if bpy.data.texts.get("Materials"):
        for matfile in bpy.data.texts.get("Materials").lines:
            createMaterialsFromMTL(matfile.body)
            

    # test call
    bpy.ops.import_test.some_data('INVOKE_DEFAULT')

