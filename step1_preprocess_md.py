from utils.md_preprocessing import (read_file, simplify_chinese_characters, remove_image,headers_correction,
                                    lines_to_md, table_clean, tables_transform)
import os

def preprocessing(name, path = 'data/clean_data'):
    file = read_file(f'data/raw_data/{name}.md')
    file = simplify_chinese_characters(file)
    file = remove_image(file)

    file_header = headers_correction(file)

    cleaned_file = table_clean(file_header)
    lines_to_md(cleaned_file, f'{name}_cleaned_combined',
                path=path)

    file_ = read_file(f'data/clean_data/{name}_cleaned_combined.md')
    final_file = tables_transform(file_)
    lines_to_md(final_file, f'{name}_',
                path=path)
    # 删除中间文件
    os.remove(f'data/clean_data/{name}_cleaned_combined.md')


if __name__ == '__main__':
    preprocessing('网易云音乐2025年中（1-6月）业绩报告')
    preprocessing('网易云音乐2025年度（1-12月）业绩报告')