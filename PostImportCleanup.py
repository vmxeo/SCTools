import bpy, bmesh
context = bpy.context 
scene = context.scene

option_deleteproxymat = True
option_offsetdecals = False


def main(context):
    for ob in context.scene.objects:
        print(ob)


def importCleanup(context):
    bpy.ops.material.materialutilities_merge_base_names(is_auto=True)
    
    for obj in scene.objects[:]:
     
        split = obj.name.split(".")
        obj.name = obj.name.replace('_out',"")
        #obj.name = obj.name.split(".")[0]
        locators_objs = [obj for obj in bpy.data.objects if obj.name.startswith(split[0])]

        if obj.type == "MESH":      
            obj.data.use_auto_smooth = True        
            
            for index, slot in enumerate(obj.material_slots):
                #select the verts from faces with material index
                if not slot.material:
                    # empty slot
                    continue
                verts = [v for f in obj.data.polygons 
                       if f.material_index == index for v in f.vertices]
                if "proxy" in slot.material.name and option_deleteproxymat:
                    print(obj.name)
                    obj.select_set(True)
                    bpy.context.view_layer.objects.active = obj
                    bpy.context.object.active_material_index = index
                    bpy.ops.object.mode_set(mode = 'EDIT')
                    bpy.ops.object.material_slot_select()
                    bpy.ops.mesh.delete(type='FACE')
                    bpy.ops.object.mode_set(mode = 'OBJECT')
                    bpy.ops.object.select_all(action='DESELECT')
                if len(verts):
                    vg = obj.vertex_groups.get(slot.material.name)
                    if vg is None: 
                        vg = obj.vertex_groups.new(name=slot.material.name)
                    vg.add(verts, 1.0, 'ADD')       
                if ("pom" in slot.material.name) or ("decal" in slot.material.name) and option_offsetdecals:
                    mod_name = slot.material.name + " tweak"
                    if not obj.modifiers.get(mod_name):
                            obj.modifiers.new(mod_name, 'DISPLACE')
                            obj.modifiers[mod_name].vertex_group = slot.material.name
                            obj.modifiers[mod_name].strength = 0.001
                            obj.modifiers[mod_name].mid_level = 0    
                            
            if not obj.modifiers.get("Weighted Normal"):
                obj.modifiers.new("Weighted Normal", 'WEIGHTED_NORMAL')
                obj.modifiers["Weighted Normal"].keep_sharp = True


        elif obj.type == "EMPTY":
            obj.empty_display_size=.1
            if "hardpoint" in obj.name:
                obj.show_name = False
                obj.empty_display_type = 'SPHERE'
                obj.scale = (1,1,1)  
                #obj.show_in_front = True
            elif "light" in obj.name:
                obj.empty_display_type = 'SINGLE_ARROW'
            elif "$" in obj.name:
                obj.empty_display_type = 'SPHERE'
            elif "$physics" in obj.name:
                bpy.data.objects.remove(obj, do_unlink=True)
                continue        
            
        
        if "DM_" in obj.name:
            if bpy.data.collections.find("Damaged") == -1:
                bpy.data.collections.new("Damaged")
            #bpy.data.collections['Damaged'].objects.link(obj)            
        elif "Interior" in obj.name:
            if bpy.data.collections.find("Interior") == -1:
                bpy.data.collections.new("Interior")
            #bpy.data.collections['Interior'].objects.link(obj)

    bpy.ops.outliner.orphans_purge(num_deleted=0)
    return {'FINISHED'} 


class SimpleOperator(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "sctools.cleanup"
    bl_label = "Import Cleanup"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        importCleanup(context)
        return {'FINISHED'}


def menu_func_import(self, context):
    self.layout.operator(importCleanup.bl_idname, text="Clean up imported assets")

def register():
    bpy.utils.register_class(SimpleOperator)


def unregister():
    bpy.utils.unregister_class(SimpleOperator)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.sctools.cleanup()
