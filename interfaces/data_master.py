import os
from langchain_community.document_loaders import TextLoader


def get_file(file_path):
    # 读取指定路径文件的内容并返回，目前是用于读取README.md和Makefile文件的源代码
    loader = TextLoader(file_path, encoding="utf-8")
    docs = loader.load()
    return docs[0].page_content if docs else ""

def get_path_all_file(path):
    # 读取指定文件夹下所有文件的内容并拼接返回，分隔符是文件名，用于读取scripts文件夹下所有脚本文件
    all_content = []
    for root, dirs, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # 用文件名作为分隔
                all_content.append(f"===== {file} =====\n{content}\n")
            except Exception as e:
                # 读取失败可跳过或记录
                print(f"读取文件失败: {file_path}, 错误: {e}")
        # 如果只需要遍历一层目录，去掉下面这行注释
        # break
    return "\n".join(all_content)


def get_file_content(path, file_path_list):
    # 读取指定路径列表下所有文件的内容并拼接返回，分隔符是文件名，目前好像没啥用
    all_content = []
    for file_path in file_path_list:
        with open(path + "/" + file_path, "r", encoding="utf-8") as f:
            content = f.read()
        all_content.append(f"===== {file_path} =====\n{content}\n")
    return "\n".join(all_content)

def get_all_relative_filepaths(path):
    filepaths = []
    for root, dirs, files in os.walk(path):
        for file in files:
            abs_path = os.path.join(root, file)
            rel_path = os.path.relpath(abs_path, path)
            filepaths.append(rel_path)
    return filepaths

# if __name__ == "__main__":
#     path = "D:/agency-swarm-main/agency-swarm/graph_explainer-main/my_langchain/source_code"
#     filepaths = get_all_relative_filepaths(path)
#     a = filepaths[7]
#     loader = TextLoader(path + "/" + a, encoding="utf-8")
#     docs = loader.load()
#     print(docs[0].page_content)