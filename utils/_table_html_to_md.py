from bs4 import BeautifulSoup
# from md_preprocessing import read_file, lines_to_md

# step1: 合并为单行
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
    return file_cleaned

# step2: 格式处理
def html_table_to_markdown(html):
    """
    处理表头：变成单行表头
    处理表身：添加缺失字段“合计”；切分长表格（双规则：500个字符 & 小标题）
    """
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')

    # 提取所有行
    rows = table.find_all('tr')

    # 表头
    first_header = rows[0].find_all('td')
    first_cell = first_header[0]
    single_line_header = ""
    header_width = 0

    # 多行表头：处理各种格式的表头
    if first_cell and first_cell.has_attr('rowspan'):
        header_height = int(first_cell['rowspan'])

        if header_height == 2 and first_header[-1].get_text() in ['截至6月30日止六个月','于12月31日','截至12月31日止年度']:
            single_line_header += f"| {first_header[-1].get_text()} |"

            # 处理第二格是2列“附注”的情况
            if first_header[1].has_attr('rowspan'):
                single_line_header += " " + first_header[1].get_text(strip=True) + " |"
                header_width += 1

            second_header = rows[1].find_all('td')
            header_width += len(second_header) + 1
            for cell in second_header:
                single_line_header += " " + cell.get_text(strip=True) + " |"

        elif header_height == 3 and first_header[1].get_text() in ['截至6月30日止六个月','于12月31日','截至12月31日止年度']:
            if len(first_header) == 2:
                single_line_header += f"| {first_header[1].get_text()}_" + rows[2].find_all('td')[-1].get_text(strip=True) + " |"

                second_header = rows[1].find_all('td')
                header_width += len(second_header) + 1
                for cell in second_header:
                    single_line_header += " " + cell.get_text(strip=True) + " |"

            elif len(first_header) == 3:
                # print(first_header)
                last_column_name = first_header[-1].get_text()

                single_line_header += f"| {first_header[1].get_text()}_" + rows[2].find_all('td')[-1].get_text(strip=True) + " |"

                second_header = rows[1].find_all('td')
                header_width += len(second_header) + 1
                for cell in second_header:
                    single_line_header += " " + cell.get_text(strip=True) + " |"

                single_line_header += " " + last_column_name
                header_width += 1
        # if header_height == 3 and first_header[-1].get_text() == '截至6月30日止六个月':
    # 单行表头：若第一个格子为空
    elif first_cell.name == 'td' and not first_cell.get_text(strip=True):
        header_height = 1
        single_line_header += "|"
        header_width = len(first_header)
        for cell in first_header:
            single_line_header += " " + cell.get_text(strip=True) + " |"
    # 没有表头
    else:
        header_height = 0

    #################################

    if header_height > 0:
        # 加分割线
        single_line_header += '\n' + "|:---" * header_width + "|" + "\n"

        table_list = []
        markdown = [single_line_header]
        # print('表头长度：', len(markdown))

        last_subtitle_idx = None
        removed_rows = 0

        rows_body = rows[header_height:]
        # 处理表身
        for i, row in enumerate(rows_body):
            cols = row.find_all(['td'])

            # 识别子标题 存储最新位置
            if cols[0].get_text(strip=True) and all([col.get_text(strip=True) == "" for col in cols[1:]]):
                # print('找到子标题：', cols[0].get_text(strip=True))
                # last_subtitle_idx = i
                last_row = rows_body[i-1].find_all(['td'])
                # print (last_row)
                if last_row[0].get_text(strip=True) and all([col.get_text(strip=True) == "" for col in last_row[1:]]):
                    pass
                else:
                    # print('找到子标题：', cols[0].get_text(strip=True))
                    last_subtitle_idx = i-removed_rows

            # 提取文本，处理空单元格(填补第一格空缺为“合计”）
            row_data = ['合计' if not cols[0].get_text(strip=True) else cols[0].get_text(strip=True)]
            row_data += [col.get_text(strip=True) if col.get_text(strip=True) else '-' for col in cols[1:]]

            markdown.append( "| " + " | ".join(row_data) + " |\n")

            # print('总长度：',len(''.join(markdown)))

            if len(''.join(markdown))>500:
                if last_subtitle_idx is None:
                    subtable = ''.join(markdown[:i + 1])
                    # print(subtable, len(subtable))
                    table_list.append(subtable)
                    markdown = [single_line_header]+markdown[i+1:]
                else:
                    # print(last_subtitle_idx)
                    subtable = ''.join(markdown[:last_subtitle_idx+1 ])
                    # print(subtable, len(subtable))
                    table_list.append(subtable)
                    markdown = [single_line_header]+markdown[last_subtitle_idx+1:]
                    removed_rows += last_subtitle_idx
                    last_subtitle_idx = None
                    # print("小标题切割")

        markdown = ''.join(markdown)
        table_list.append(markdown)

    else: #header_height == 0:
        markdown = ""
        for row in rows:
            cols = row.find_all(['td'])
            row_data = [col.get_text(strip=True) if col.get_text(strip=True) else '-' for col in cols]
            markdown += ''.join(row_data) + '。\n\n'

        table_list = [markdown]

    return '\n'.join(table_list)

if __name__ == '__main__':
    pass
# # step1 测试
# # file = ['aaa\n','bbb\n','\n','/\n','ccc','ddd','eee']
# file = read_file('../data/clean_data/网易云音乐2025年中业绩报告_cleaned.md')
# print('original file',file)
# cleaned_file = table_clean(file)
# print(cleaned_file)
# lines_to_md(cleaned_file, '网易云音乐2025年中业绩报告_cleaned_plus',
#             path='../data/clean_data')


# step2 测试
# 2行标准
html_table = '<table><tr><td rowspan="2"></td><td colspan="2">截至6月30日止六个月</td></tr><tr><td>2025年 人民币千元 (未经审计)</td><td>2024年 人民币千元 (未经审计)</td></tr><tr><td>于1月1日</td><td>7,274</td><td>6,951</td></tr><tr><td>期内减值亏损拨备／(拨回)净额</td><td>3,998</td><td>(1,034)</td></tr><tr><td>于6月30日</td><td>11,272</td><td>5,917</td></tr></table>'
# 1行
html_table2 = '<table><tr><td></td><td>于2025年6月30日人民币千元(未经审计)</td><td>于2024年12月31日人民币千元(经审计)</td></tr><tr><td>应收账款</td><td>1,133,175</td><td>1,061,705</td></tr><tr><td>减:亏损拨备</td><td>(11,272)</td><td>(7,274)</td></tr><tr><td>应收账款,净值</td><td>1,121,903</td><td>1,054,431</td></tr><tr><td>应收票据</td><td>327</td><td>222</td></tr><tr><td></td><td>1,122,230</td><td>1,054,653</td></tr></table>'
# 2行，有2列的附注, 长表格
html_table3 = '<table><tr><td rowspan="2"></td><td rowspan="2">附注</td><td colspan="2">截至6月30日止六个月</td></tr><tr><td>2025年 人民币千元 (未经审计)</td><td>2024年 人民币千元 (未经审计)</td></tr><tr><td>收入</td><td>2</td><td>3,827,117</td><td>4,070,493</td></tr><tr><td>营业成本</td><td>3</td><td>(2,434,632)</td><td>(2,644,762)</td></tr><tr><td>毛利</td><td></td><td>1,392,485</td><td>1,425,731</td></tr><tr><td>销售及市场费用</td><td>3</td><td>(163,379)</td><td>(369,427)</td></tr><tr><td>一般费用及管理费用</td><td>3</td><td>(92,968)</td><td>(89,750)</td></tr><tr><td>研发费用</td><td>3</td><td>(378,878)</td><td>(395,647)</td></tr><tr><td>其他收入</td><td></td><td>84,689</td><td>21,178</td></tr><tr><td>其他净收益</td><td></td><td>2,557</td><td>7,848</td></tr><tr><td>营业利润</td><td></td><td>844,506</td><td>599,933</td></tr><tr><td>应占使用权益法计算的投资业绩</td><td></td><td>450</td><td>(753)</td></tr><tr><td>财务收入</td><td></td><td>223,200</td><td>214,529</td></tr><tr><td>财务成本</td><td></td><td>(96)</td><td>(131)</td></tr><tr><td>所得税前利润</td><td></td><td>1,068,060</td><td>813,578</td></tr><tr><td>所得税抵免／(费用)</td><td>4</td><td>814,082</td><td>(3,629)</td></tr><tr><td>期内利润</td><td></td><td>1,882,142</td><td>809,949</td></tr><tr><td>期内利润／(亏损)归属于：</td><td></td><td></td><td></td></tr><tr><td>本公司权益持有人</td><td></td><td>1,885,499</td><td>809,832</td></tr><tr><td>非控股权益</td><td></td><td>(3,357)</td><td>117</td></tr><tr><td></td><td></td><td>1,882,142</td><td>809,949</td></tr><tr><td>归属于本公司权益持有人的每股盈利   (每股以人民币列示)</td><td></td><td></td><td></td></tr><tr><td>每股基本盈利</td><td>5</td><td>8.96</td><td>3.88</td></tr><tr><td>每股摊薄盈利</td><td>5</td><td>8.85</td><td>3.84</td></tr></table>'
# 3行
html_table4 = '<table><tr><td rowspan="3"></td><td colspan="2">截至6月30日止六个月</td></tr><tr><td>2025年(未经审计)</td><td>2024年(未经审计)</td></tr><tr><td colspan="2">(人民币千元)</td></tr><tr><td>营业利润</td><td>844,506</td><td>599,933</td></tr><tr><td>加：</td><td></td><td></td></tr><tr><td>股本结算的股权款项附注(1)</td><td>60,854</td><td>70,917</td></tr><tr><td>经调整营业利润</td><td>905,360</td><td>670,850</td></tr><tr><td>本公司权益持有人应占期内利润</td><td>1,885,499</td><td>809,832</td></tr><tr><td>加：</td><td></td><td></td></tr><tr><td>股本结算的股权款项附注(1)</td><td>60,854</td><td>70,917</td></tr><tr><td>经调整净利润</td><td>1,946,353</td><td>880,749</td></tr></table>'
# 3行最复杂
html_table5 = '<table><tr><td rowspan="3"></td><td colspan="2">截至6月30日止六个月</td><td rowspan="2">变动(%)</td></tr><tr><td>2025年(未经审计)</td><td>2024年(未经审计)</td></tr><tr><td colspan="3">(人民币千元,百分比除外)</td></tr><tr><td>收入</td><td>3,827,117</td><td>4,070,493</td><td>-6.0%</td></tr><tr><td>毛利</td><td>1,392,485</td><td>1,425,731</td><td>-2.3%</td></tr><tr><td>营业利润</td><td>844,506</td><td>599,933</td><td>+40.8%</td></tr><tr><td>除所得税前利润</td><td>1,068,060</td><td>813,578</td><td>+31.3%</td></tr><tr><td>期内利润(1)</td><td>1,882,142</td><td>809,949</td><td>+132.4%</td></tr><tr><td>非《国际财务报告准则》计量(2):</td><td></td><td></td><td></td></tr><tr><td>经调整营业利润</td><td>905,360</td><td>670,850</td><td>+35.0%</td></tr><tr><td>经调整净利润</td><td>1,946,353</td><td>880,749</td><td>+121.0%</td></tr></table>'
# 带小标题的长表格
html_table6 = '<table><tr><td></td><td>附注</td><td>于2025年6月30日人民币千元(未经审计)</td><td>于2024年12月31日人民币千元(经审计)</td></tr><tr><td>资产</td><td></td><td></td><td></td></tr><tr><td>非流动资产</td><td></td><td></td><td></td></tr><tr><td>物业、厂房及设备</td><td></td><td>19,757</td><td>20,080</td></tr><tr><td>使用权资产</td><td></td><td>5,651</td><td>6,165</td></tr><tr><td>使用权益法计算的投资</td><td></td><td>60,505</td><td>72,425</td></tr><tr><td>递延所得税资产</td><td></td><td>849,384</td><td>-</td></tr><tr><td>预付内容许可费</td><td></td><td>99,826</td><td>107,173</td></tr><tr><td>预付款、押金及其他应收款</td><td></td><td>40,409</td><td>24,221</td></tr><tr><td>银行存款</td><td></td><td>1,400,000</td><td>1,400,000</td></tr><tr><td></td><td></td><td>2,475,532</td><td>1,630,064</td></tr><tr><td>流动资产</td><td></td><td></td><td></td></tr><tr><td>应收账款及应收票据</td><td>7</td><td>1,122,230</td><td>1,054,653</td></tr><tr><td>预付内容许可费</td><td></td><td>373,525</td><td>335,144</td></tr><tr><td>预付款、押金及其他应收款</td><td></td><td>245,276</td><td>305,139</td></tr><tr><td>应收集团公司款项</td><td></td><td>37,540</td><td>32,993</td></tr><tr><td>按公允价值计量且其变动计入损益的金融资产</td><td></td><td>6,584</td><td>6,515</td></tr><tr><td>银行存款</td><td></td><td>8,949,823</td><td>6,420,669</td></tr><tr><td>受限制现金</td><td></td><td>407</td><td>1,862</td></tr><tr><td>现金及现金等价物</td><td></td><td>2,076,513</td><td>3,795,210</td></tr><tr><td></td><td></td><td>12,811,898</td><td>11,952,185</td></tr><tr><td>资产总额</td><td></td><td>15,287,430</td><td>13,582,249</td></tr><tr><td>权益</td><td></td><td></td><td></td></tr><tr><td>归属于本公司权益持有人的权益</td><td></td><td></td><td></td></tr><tr><td>股本</td><td></td><td>139</td><td>139</td></tr><tr><td>其他储备金</td><td></td><td>18,761,836</td><td>18,708,160</td></tr><tr><td>累计亏损</td><td></td><td>(6,645,858)</td><td>(8,530,648)</td></tr><tr><td></td><td></td><td>12,116,117</td><td>10,177,651</td></tr><tr><td>非控股权益</td><td></td><td>505</td><td>3,862</td></tr><tr><td>权益总额</td><td></td><td>12,116,622</td><td>10,181,513</td></tr><tr><td>负债</td><td></td><td></td><td></td></tr><tr><td>非流动负债</td><td></td><td></td><td></td></tr><tr><td>合约负债</td><td></td><td>97,623</td><td>83,889</td></tr><tr><td>租赁负债</td><td></td><td>4,302</td><td>4,762</td></tr><tr><td></td><td></td><td>101,925</td><td>88,651</td></tr><tr><td>流动负债</td><td></td><td></td><td></td></tr><tr><td>应付账款</td><td>8</td><td>50,817</td><td>24,015</td></tr><tr><td>预提费用及其他应付款</td><td></td><td>1,611,644</td><td>1,976,447</td></tr><tr><td>合约负债</td><td></td><td>1,309,697</td><td>1,235,473</td></tr><tr><td>应付集团公司款项</td><td></td><td>64,620</td><td>73,702</td></tr><tr><td>应付所得税</td><td></td><td>30,494</td><td>738</td></tr><tr><td>租赁负债</td><td></td><td>1,611</td><td>1,710</td></tr><tr><td></td><td></td><td>3,068,883</td><td>3,312,085</td></tr><tr><td>负债总额</td><td></td><td>3,170,808</td><td>3,400,736</td></tr><tr><td>权益及负债总额</td><td></td><td>15,287,430</td><td>13,582,249</td></tr></table>'
# 验证表格切分时小标题丢失问题
html_table7 = '<table><tr><td rowspan="2"></td><td colspan="2">截至6月30日止六个月</td></tr><tr><td>附注</td><td>2025年人民币千元(未经审计)</td></tr><tr><td>期内利润</td><td></td><td>1,882,142</td></tr><tr><td>其他综合(亏损)/收益:</td><td></td><td></td></tr><tr><td>将不会重新分类到损益的项目</td><td></td><td></td></tr><tr><td>货币折算差额</td><td></td><td>(82,453)</td></tr><tr><td>将会重新分类到损益的项目</td><td></td><td></td></tr><tr><td>货币折算差额</td><td></td><td>(1,950)</td></tr><tr><td>期内综合收益总额</td><td></td><td>1,797,739</td></tr><tr><td>期内综合(亏损)/收益总额归属于:</td><td></td><td></td></tr><tr><td>本公司权益持有人</td><td></td><td>1,801,096</td></tr><tr><td>非控股权益</td><td></td><td>(3,357)</td></tr><tr><td></td><td></td><td>1,797,739</td></tr></table>'


# 转换并打印
# markdown_output = html_table_to_markdown(html_table)
# markdown_output2 = html_table_to_markdown(html_table2)
# markdown_output3 = html_table_to_markdown(html_table3)
# markdown_output4 = html_table_to_markdown(html_table4)
# markdown_output5 = html_table_to_markdown(html_table5)
# markdown_output6 = html_table_to_markdown(html_table6)
# markdown_output7 = html_table_to_markdown(html_table7)

# print(markdown_output)
# print(markdown_output2)
# print(markdown_output3)
# print(len(markdown_output3))
# print(markdown_output4)
# print(markdown_output5)

# print(markdown_output6)
# print(len(markdown_output6))

# print(markdown_output7)



# i = None
# print(i==None)
# i = 1
# print(i==None)