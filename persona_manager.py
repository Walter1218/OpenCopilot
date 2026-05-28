import os
import glob

class PersonaManager:
    """数据层：管理 personas 目录下的 .md 文件"""
    def __init__(self, base_dir=None):
        if base_dir is None:
            self.base_dir = os.path.join(os.path.dirname(__file__), "personas")
        else:
            self.base_dir = base_dir
        
        # 内置的、不可被删除（但可修改内容，或者限制完全不可删除）的系统核心 Persona
        self.built_in_personas = ["default", "code", "translate", "polish", "custom", "revision"]
        
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
            
    def _get_path(self, name):
        """支持获取相对路径，例如 'office/academic/paper'"""
        if not name.endswith(".md"):
            name += ".md"
        return os.path.join(self.base_dir, name)
        
    def list_personas(self):
        """获取所有 persona 名字，去除 .md 后缀，包含子目录"""
        personas = []
        pattern = os.path.join(self.base_dir, "**", "*.md")
        for filepath in glob.glob(pattern, recursive=True):
            # 获取相对于 base_dir 的路径
            rel_path = os.path.relpath(filepath, self.base_dir)
            # 去除 .md 后缀
            name = rel_path[:-3]
            personas.append(name)
        return sorted(personas)
        
    def get_persona(self, name):
        """读取指定 persona 的内容"""
        filepath = self._get_path(name)
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
            
    def save_persona(self, name, content):
        """保存 persona 内容（新建或覆盖）"""
        filepath = self._get_path(name)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True
        
    def delete_persona(self, name):
        """删除 persona。阻止删除内置的。"""
        # 防止误删核心
        base_name = os.path.basename(name)
        if base_name in self.built_in_personas or name in self.built_in_personas:
            return False, "内置角色无法删除，只能修改。"
            
        filepath = self._get_path(name)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                # 尝试清理空目录
                dir_path = os.path.dirname(filepath)
                if dir_path != self.base_dir and not os.listdir(dir_path):
                    os.rmdir(dir_path)
                return True, "删除成功"
            except Exception as e:
                return False, str(e)
        return False, "文件不存在"