import sqlite3
from typing import List, Dict, Optional
import os
import logging

logger = logging.getLogger(__name__)

class SQLiteManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        logger.info(f"初始化SQLiteManager: {db_path}")

    def _connect(self) -> sqlite3.Connection:
        """连接数据库；新版客户端缓存使用 file_meta 表，映射为 cache_file"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.create_collation("baidunetdisksort", lambda a, b: ((a or "") > (b or "")) - ((a or "") < (b or "")))
            tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            if 'cache_file' not in tables and 'file_meta' in tables:
                conn.execute("CREATE TEMP VIEW cache_file AS SELECT * FROM file_meta")
        except sqlite3.Error as e:
            logger.warning(f"检查缓存表结构失败: {e}")
        return conn
        
    def get_database_info(self) -> Dict:
        """获取数据库基本信息"""
        logger.info(f"获取数据库信息: {self.db_path}")
        try:
            conn = self._connect()
            cursor = conn.cursor()
            
            # 计算所有文件的总大小
            cursor.execute("SELECT SUM(file_size) FROM cache_file WHERE isdir = 0")
            total_size = cursor.fetchone()[0] or 0
            logger.info(f"总文件大小: {total_size}")
            
            # 计算文件和文件夹的数量
            cursor.execute("SELECT COUNT(*) FROM cache_file WHERE isdir = 0")
            file_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM cache_file WHERE isdir = 1")
            dir_count = cursor.fetchone()[0]
            logger.info(f"文件数: {file_count}, 文件夹数: {dir_count}")
            
            # 获取数据库文件名
            db_name = os.path.basename(self.db_path)
            
            conn.close()
            
            return {
                "name": '/',
                "total_size": total_size,
                "file_count": file_count,
                "dir_count": dir_count
            }
        except sqlite3.Error as e:
            logger.error(f"数据库错误: {str(e)}")
            raise Exception(f"Database error: {str(e)}")
            
    def get_directory_tree(self, node_id: str) -> Dict:
        """获取指定节点下的目录树及大小信息
        
        Args:
            node_id: 节点ID，根节点使用'0'或'/'
        """
        logger.info(f"获取目录树，节点ID: {node_id}")
        try:
            conn = self._connect()
            cursor = conn.cursor()
            
            # 获取当前节点的parent_path和server_filename
            if node_id in ['0', '/']:
                parent_path = '/'
                current_size = 0
            else:
                cursor.execute("""
                    SELECT parent_path, server_filename, file_size
                    FROM cache_file
                    WHERE id = ?
                """, (node_id,))
                result = cursor.fetchone()
                if not result:
                    raise Exception(f"Node not found: {node_id}")
                parent_path, filename, current_size = result
                parent_path = f"{parent_path}{filename}/"
            
            # 获取直接子项及其大小
            query = """
                SELECT 
                    f1.id,
                    f1.server_filename,
                    f1.isdir,
                    CASE 
                        WHEN f1.isdir = 1 THEN (
                            SELECT SUM(f2.file_size)
                            FROM cache_file f2
                            WHERE f2.parent_path LIKE ? || f1.server_filename || '/%' AND f2.isdir = 0
                        )
                        ELSE f1.file_size
                    END as size
                FROM cache_file f1
                WHERE f1.parent_path = ?
                ORDER BY isdir desc,size DESC
            """
            logger.info(f"执行查询: {query} with parent_path={parent_path}")
            cursor.execute(query, (parent_path, parent_path))
            items = cursor.fetchall()
            logger.info(f"查询到 {len(items)} 个项目")
            
            # 处理结果
            children = []
            total_size = 0
            
            for id, name, isdir, size in items:
                if size is None:
                    size = 0
                total_size += size
                children.append({
                    "id": str(id),
                    "name": name,
                    "value": size,
                    "path": str(id),
                    "isdir": bool(isdir)
                })
            
            conn.close()
            logger.info(f"总大小: {total_size}, 子项目数: {len(children)}")
            
            return {
                "id": node_id,
                "size": total_size or current_size,
                "children": children
            }
        except sqlite3.Error as e:
            logger.error(f"数据库错误: {str(e)}")
            raise Exception(f"Database error: {str(e)}") 

    def get_large_files(self, node_id: str, min_size: int = 100 * 1024 * 1024) -> List[Dict]:
        """获取指定节点下大于min_size的所有文件，按文件大小倒序排列
        Args:
            node_id: 节点ID，根节点使用'0'或'/'
            min_size: 最小文件大小，默认100M
        Returns:
            List[Dict]: 文件信息列表
        """
        logger.info(f"获取大文件，节点ID: {node_id}, 最小大小: {min_size}")
        try:
            conn = self._connect()
            cursor = conn.cursor()

            # 获取当前节点的parent_path和server_filename
            if node_id in ['0', '/']:
                parent_path = '/'
            else:
                cursor.execute("""
                    SELECT parent_path, server_filename
                    FROM cache_file
                    WHERE id = ?
                """, (node_id,))
                result = cursor.fetchone()
                if not result:
                    raise Exception(f"Node not found: {node_id}")
                parent_path, filename = result
                parent_path = f"{parent_path}{filename}/"

            # 查询该目录及其所有子目录下的大文件
            query = """
                SELECT id, server_filename, file_size, parent_path
                FROM cache_file
                WHERE isdir = 0
                  AND parent_path LIKE ? || '%'
                  AND file_size >= ?
                ORDER BY file_size DESC
            """
            logger.info(f"执行查询: {query} with parent_path={parent_path}, min_size={min_size}")
            cursor.execute(query, (parent_path, min_size))
            items = cursor.fetchall()
            logger.info(f"查询到 {len(items)} 个大文件")

            files = []
            for id, name, size, ppath in items:
                files.append({
                    "id": str(id),
                    "name": name,
                    "size": size,
                    "parent_path": ppath
                })

            conn.close()
            return files
        except sqlite3.Error as e:
            logger.error(f"数据库错误: {str(e)}")
            raise Exception(f"Database error: {str(e)}") 

    def get_duplicate_files(self, node_id: str, min_size: int = 10 * 1024 * 1024) -> List[Dict]:
        """获取指定节点下重复的文件（md5相同）
        
        Args:
            node_id: 节点ID，根节点使用'0'或'/'
            min_size: 最小文件大小，默认10M
            
        Returns:
            List[Dict]: 重复文件组列表，每组包含相同md5的文件
        """
        logger.info(f"获取重复文件，节点ID: {node_id}, 最小大小: {min_size}")
        try:
            conn = self._connect()
            cursor = conn.cursor()

            # 获取当前节点的parent_path
            if node_id in ['0', '/']:
                parent_path = '/'
            else:
                cursor.execute("""
                    SELECT parent_path, server_filename
                    FROM cache_file
                    WHERE id = ?
                """, (node_id,))
                result = cursor.fetchone()
                if not result:
                    raise Exception(f"Node not found: {node_id}")
                parent_path, filename = result
                parent_path = f"{parent_path}{filename}/"

            # 查询该目录及其所有子目录下的大文件，按md5分组
            query = """
                WITH duplicate_groups AS (
                    SELECT md5, COUNT(*) as count, SUM(file_size) as total_size
                    FROM cache_file
                    WHERE isdir = 0
                      AND parent_path LIKE ? || '%'
                      AND file_size >= ?
                      AND md5 IS NOT NULL
                    GROUP BY md5
                    HAVING COUNT(*) > 1
                )
                SELECT 
                    f.id,
                    f.server_filename,
                    f.file_size,
                    f.parent_path,
                    f.md5,
                    dg.count as duplicate_count,
                    dg.total_size
                FROM cache_file f
                JOIN duplicate_groups dg ON f.md5 = dg.md5
                WHERE f.parent_path LIKE ? || '%'
                  AND f.file_size >= ?
                ORDER BY f.file_size DESC, f.md5
            """
            
            logger.info(f"执行查询: {query} with parent_path={parent_path}, min_size={min_size}")
            cursor.execute(query, (parent_path, min_size, parent_path, min_size))
            items = cursor.fetchall()
            logger.info(f"查询到 {len(items)} 个重复文件")

            # 按md5分组处理结果
            groups = {}
            for id, name, size, ppath, md5, count, total_size in items:
                if md5 not in groups:
                    groups[md5] = {
                        "md5": md5,
                        "count": count,
                        "total_size": total_size,
                        "files": []
                    }
                groups[md5]["files"].append({
                    "id": str(id),
                    "name": name,
                    "size": size,
                    "parent_path": ppath
                })

            # 转换为列表并按总大小排序
            result = list(groups.values())
            result.sort(key=lambda x: x["total_size"], reverse=True)

            conn.close()
            return result
        except sqlite3.Error as e:
            logger.error(f"数据库错误: {str(e)}")
            raise Exception(f"Database error: {str(e)}") 
