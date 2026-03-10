from bs4 import BeautifulSoup
import re

from utils._table_html_to_md import html_table_to_markdown

def read_file(file_path):
    """返回list，里面是每行的内容"""
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    return lines

def remove_image(file):
    """删除顶部的图标logo"""
    filtered_lines = []
    counter = 0
    for line in file:
        if line.startswith('![image]'):
            counter += 1
            continue
        filtered_lines.append(line)
    print(f'一共移除了{counter}张图片')
    return filtered_lines

def simplify_chinese_characters(file):
    """将繁体中文字符转为简体中文字符"""
    from zhconv import convert
    file_simplified = []
    for line in file:
        file_simplified.append(convert(line, 'zh-cn'))
    return file_simplified

def headers_correction(file):
    """修正标题"""
    file_cleaned = []
    level = 1
    pattern =''
    last_pattern = ''
    for i,line in enumerate(file):
        if line.startswith('#') and line!='# 网易云音乐\n':
            if len(line) > 4 and re.match(r'^# [1-9][0-9]? \b', line[:5]): # 1
                print(111,line)
                pattern = '1'
                level = 3
            elif len(line)>6 and re.match(r'^# [1-9][0-9]?\.[1-9][0-9]?\b', line[:7]): # 1.1
                print('1.1',line)
                pattern = '1.1'
                level = 4
            elif len(line) > 4 and re.match(r'^# \([a-z]\)', line[:5]): # (a)
                print('(a)',line)
                pattern = '(a)'
            elif line == '# 报告期间后事项\n' or line == '# 報告期間後事項\n':
                print('回到1')
                level = 1
            print('----',level,line)

            if level == 2:
                if file[i + 2].startswith('#'):  # 下一行也是标题
                    line = line.replace('#', '##')
                    print('2-3 ',line)
                else:
                    line = line.replace('#', '###')
            elif level == 1:
                line = line.replace('#', '##')
                if file[i + 2].startswith('#'):
                    print('进入二级', file[i + 2])
                    level = 2
            elif level == 3:
                line = line.replace('#', '###')
                level = 4
            elif level == 4:
                a = len(line)>6 and re.match(r'^# [1-9][0-9]?\.[1-9][0-9]?\b', line[:7])
                b = len(line) > 4 and re.match(r'^# \([a-z]\)', line[:5])
                if not(a or b):
                    pattern = '字'
                    print("98999988")
                line = line.replace('#', '####')

                print(pattern, last_pattern)
                if (not((pattern == '(a)' and last_pattern =='1')or(pattern == '(a)' and last_pattern =='(a)'))
                        and
                    pattern != '字'):
                    level = 5
            elif level == 5:
                line = line.replace('#', '#####')
            last_pattern = pattern

        file_cleaned.append(line)
    return file_cleaned

def lines_to_md(file, name, path = 'data/clean_data'):
    """将 list of texts 转为md文件"""
    with open(f'{path}/{name}.md', 'w', encoding='utf-8') as file_md:
        for line in file:
            file_md.write(line)


# 表格处理step1: 合并为单行
def table_clean(file):
    """解决一张表被错误分行的问题"""
    file_cleaned = ['']
    for i in range(len(file)-1):

        if file[i] != '\n' and file[i+1] != '\n':
            if file[i][-1] == '\n':
                add_line = file[i][:-1]
            else:
                add_line = file[i]
            file_cleaned[-1] += add_line
        else:
            file_cleaned.append(file[i])
    print('表格处理完成！')
    return file_cleaned

def tables_transform(file_cleaned):
    # file_cleaned = table_clean(file)
    # print(file_cleaned)
    counter = 0
    file_final = []
    for line in file_cleaned:
        # print(line)
        # print(line[:8])
        if line.startswith('\n<table>') or line.startswith('<table>'):
            # print(line)
            counter += 1
            file_final.append(html_table_to_markdown(line))
        else:
            file_final.append(line)
    return file_final

if __name__ == '__main__':
    file_ = read_file('../data/raw_data/网易云音乐2025年中（1-6月）业绩报告.md')
    print(file_)
    cleaned_file = headers_correction(file_)
    lines_to_md(cleaned_file, '网易云音乐2025年中（1-6月）业绩报告_cleaned',
                path='../data/clean_data')

    file_ = read_file('../data/raw_data/网易云音乐2025年度（1-12月）业绩报告.md')
    print(file_)
    cleaned_file = headers_correction(file_)
    lines_to_md(cleaned_file, '网易云音乐2025年度（1-12月）业绩报告_cleaned',
                path='../data/clean_data')


# file_ = read_file('../data/clean_data/网易云音乐2025年中业绩报告_cleaned.md')
# cleaned_file = table_clean(file_)
# lines_to_md(cleaned_file, '网易云音乐2025年中业绩报告_cleaned_combined',
#             path='../data/clean_data')
#
# file_ = read_file('../data/clean_data/网易云音乐2025年中业绩报告_cleaned_combined.md')
# final_file = tables_transform(file_)
# lines_to_md(final_file, '网易云音乐2025年中业绩报告_表格已处理',
#             path='../data/clean_data')

