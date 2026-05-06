import os,hashlib
from utils.logger_handler import logger
import sys
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader,TextLoader
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
def get_file_md5_hex(file_path:str):#获取文件的md5的十六进制字符串
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return 
    if not os.path.isfile(file_path):
        logger.error(f"[md5计算]路径 {file_path}不是文件")
        return 
    md5_obj=hashlib.md5()
    chunk_size=4096  #4KB防止文件过大爆内存
    try:
        with open(file_path,"rb")as f:  #必须二进制读取
            while chunk:=f.read(chunk_size):
                md5_obj.update(chunk)
        md5_hex=md5_obj.hexdigest()
        return md5_hex
    except Exception as e:
        logger.error(f"[md5计算]文件 {file_path} 读取失败: {str(e)}")
        return None

def listdir_with_allowed_type(path:str,allowed_types:tuple[str]):#返回文件夹内的文件列表(允许的文件后缀)
    files=[]
    if not os.path.isdir(path):
        logger.error(f"[listdir_with_alloed_type] {path}不是文件夹")
        return []
    for f in os.listdir(path):
        if f.endswith(allowed_types):
            files.append(os.path.join(path,f))
    return tuple(files)
def pdf_loader(file_path:str,passwd=None)->list[Document]:#加载pdf文件
    return PyPDFLoader(file_path,passwd).load()

def txt_loader(file_path:str)->list[Document]:#加载txt文件
    return TextLoader(file_path,encoding="utf-8").load()
