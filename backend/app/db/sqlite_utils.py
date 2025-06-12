import sqlite3
from typing import List, Dict, Optional
import os
import logging

logger = logging.getLogger(__name__)

class SQLiteManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        logger.info(f"初始化SQLiteManager: {db_path}")
        
    def get_database_info(self) -> Dict:
        """获取数据库基本信息"""
        logger.info(f"获取数据库信息: {self.db_path}")
        try:
            conn = sqlite3.connect(self.db_path)
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
            conn = sqlite3.connect(self.db_path)
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