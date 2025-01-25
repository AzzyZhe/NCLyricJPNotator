"""
Todo（但是大概会鸽了）
confirm_matches: 连续汉字片假名才手动处理
generate_regex_pattern: 处理标点统一化匹配
misc: 批处理脚本启动
"""
"""
Help
调整输出格式主要在match_format、save_to_file以及输出文件名
手动调整使用时
去除#表示将此字与后面的词合并
在平假名前加换行则是将此假名拆给后一个词用（从此行第一个平假名前也可以）
但是两个词及以上的错位（如果有）确实只能单独把片假名拷过去
"""
import sys
import os
import re
import yaml
import subprocess

# 读入罗马音对片假名的映射表
with open('romaji2hiragana.yaml', 'r', encoding='utf-8') as file: 
    roma2hiragana = yaml.safe_load(file)

# 两行两行读入网易云复制来的歌词及注音/翻译
def read_file(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    # 去除空行
    lines = [line.strip() for line in lines if line.strip()]

    # 分组
    line1s = []
    line2s = []
    for i in range(0, len(lines), 2):
        line1s.append(lines[i])
        if i + 1 < len(lines):
            line2s.append(lines[i + 1])

    return line1s, line2s

# 输入歌词预处理
def lyric_preproc(lyrics):
    # 此处仅去除小括号在歌词中重复标注发音
    lyrics = [re.sub(r'\(.*?\)', '', line) for line in lyrics]
    return lyrics

# 替换罗马音到平假名
def roman2hiragana(text):
    # 使用正则表达式匹配连续的英文字母
    pattern = re.compile(r'[a-zA-Z]+')
    def replace(match):
        roman = match.group(0).lower()
        # 返回对应的平假名，如果找不到则返回原罗马音
        return roma2hiragana.get(roman, roman)
    return pattern.sub(replace, text)

# 由歌词生成正则匹配式、输出结果、匹配汉字片假名
def generate_regex_pattern(string1):
    pattern = ""
    result = ""
    match1 = []
    for char in string1:
        if '\u4e00' <= char <= '\u9fff':  # 汉字匹配多个平假名
            pattern += r"([ぁ-ゖ]+)"
            result += r'{}'
            match1.append(char)
        elif '\u3040' <= char <= '\u309f':  # 平假名匹配（包括可替代匹配）
            if char == 'は':  # 特殊处理：wa匹配は或わ
                pattern += r"(?:は|わ)"
            elif char == 'へ':
                pattern += r"(?:え|へ)"
            elif char == 'を':
                pattern += r"(?:お|を)"
            else:
                pattern += char
            result += char
        elif '\u30a0' <= char <= '\u30ff':  # 片假名匹配单个平假名
            pattern += r"([ぁ-ゖ])"
            result += r'{}'
            match1.append(char)
        elif char.isspace():  # 空格匹配任意多（含0）个空格
            pattern += r"\s*"
            result += char
        else:  # 其他字符原样匹配
            pattern += char
            result += char
    return pattern, result, match1

# 用正则模式串在发音中匹配
def match_notation(pattern, string2):
    regex = re.compile(pattern)
    matches = regex.finditer(string2)
    match2 = next(matches).groups() # 匹配成功时确定有唯一结果，否则报错
    return match2

# 实现的打开临时文件供手动调整匹配的套件
# 写入汉字发音匹配对到临时文件
def write_to_temp_file(match1, match2, temp_file_path='temp.txt'):
    with open(temp_file_path, 'w') as temp_file:
        for char, kana in zip(match1, match2):
            temp_file.write(f">{char}#\n{kana}\n")
# 打开编辑器并等待保存退出
def edit_temp_file(temp_file_path='temp.txt'):
    if os.name == 'nt':
        editor_process = subprocess.Popen(['notepad', temp_file_path])
    else:
        editor_process = subprocess.Popen(['nano', temp_file_path])
    editor_process.wait()
# 重新载入编辑后的匹配
def read_and_process_temp_file(temp_file_path='temp.txt'):
    with open(temp_file_path, 'r') as temp_file:
        lines = temp_file.readlines()
    match1, match2 = [], []
    current_char = ""
    current_kana = ""
    merged = 0
    toSave = False
    for line in lines:
        line = line.strip()  # 去掉行首尾的空白符
        if line.startswith(">"):  # 检测到新的汉字或片假名
            if "#" in line:  # '>汉字#'
                current_char += line.split("#")[0][1:]  # 提取汉字部分
                toSave = True # '>汉字#'行的下一行处理完保存一组
            else:  # '>汉字'格式
                current_char += line[1:]  # 提取汉字部分
                merged += 1
        else:  # 当前行是平假名，追加到当前汉字的发音
            current_kana += line
            if toSave:
                match1.append(current_char)
                match2.append(current_kana)
                current_char = ""
                current_kana = ""
                toSave = False
                for i in range(merged):
                    match1.append('')
                    match2.append('')
                merged = 0
    return match1, match2

# 手动调整平假名发音与汉字片假名的匹配
def confirm_matches(matches1, matches2, temp_file_path='temp.txt'):
    try:
        match1 = []
        match2 = []
        lengths = []
        # 放进同一个list
        for mch1, mch2 in zip(matches1, matches2):
            lengths.append(len(mch1))
            match1 += mch1
            match2 += mch2
        # 手动调整处理
        write_to_temp_file(match1, match2, temp_file_path)
        edit_temp_file(temp_file_path)
        final_match1, final_match2 = read_and_process_temp_file(temp_file_path)
        os.remove(temp_file_path)
        # 从同一个list再分出来
        final_matches1 = []
        final_matches2 = []
        now_st = 0
        for l in lengths:
            final_matches1.append(final_match1[now_st:now_st+l])
            final_matches2.append(final_match2[now_st:now_st+l])
            now_st += l        
    except Exception:
        return None, None
    return final_matches1, final_matches2

# 注音输出格式：
def match_format(p1, p2):
    # 其中p1为匹配到汉字/片假名，p2为匹配到平假名
    if p1 == '' and p2 == '':
        return ''
    return f'\overset{{{p2}}}{{{p1}}}'

# 打包构建标注完成结果
def get_notated(matches1, matches2, results):
    notateds = []
    for match1, match2, result in zip(matches1, matches2, results):
        replacement = [match_format(p1, p2) for p1, p2 in zip(match1, match2)]
        notated = result.format(*replacement)
        notateds.append(notated)
    return notateds

# 输出到文件及格式后处理
def save_to_file(filename_output, notateds, translations):
    with open(filename_output, 'w', encoding='utf-8') as file:
        for idx, notated in enumerate(notateds):
            file.write(f'${notated}$\n'.replace(' ','\\quad'))
            if translations is not None:
                file.write(f'{translations[idx]}\n')
            file.write('\n')
    print(f'已输出标注歌词到：{filename_output}')
    
# 主函数
def main():
    # 设置默认文件名
    default_romaji = 'input_jr.txt'
    default_chinese = 'input_jc.txt'
    default_output = 'output.md'
    no_translation = False
    manual_adjust = True
    
    # 从命令行参数获取文件名，如果没有提供，则使用默认值
    if len(sys.argv) > 1:
        filename_romaji = sys.argv[1]
    else:
        filename_romaji = default_romaji
    print(f"指定输入歌词罗马音文件：{filename_romaji}")
    if len(sys.argv) > 2:
        filename_chinese = sys.argv[2]
    else:
        filename_chinese = default_chinese
    print(f"指定输入歌词翻译文件  ：{filename_chinese}")
    filename_output = default_output
    
    # 检查文件是否存在
    if not os.path.exists(filename_romaji):
        print(f"错误： 输入文件 '{filename_romaji}' 不存在", file=sys.stderr)
        return 1
    if not os.path.exists(filename_romaji):
        print(f"警告： 输入文件 '{filename_romaji}' 不存在，将不使用翻译", file=sys.stderr)
        no_translation = True
    
    # 读入歌词
    lyrics, notations = read_file(filename_romaji)
    if not no_translation:
        _, translations = read_file(filename_chinese)
    else:
        translations = None
    lyrics = lyric_preproc(lyrics)
    
    # 对所有歌词进行发音匹配
    matches1 = []
    matches2 = []
    results = []
    for lyric, notation in zip(lyrics, notations):
        try:
            hiragana = roman2hiragana(notation).replace(' ','')
            pattern, result, match1 = generate_regex_pattern(lyric)
            match2 = match_notation(pattern, hiragana)
            matches1.append(match1)
            matches2.append(match2)
            results.append(result)
        except StopIteration:
            print(f'错误： 在处理\n{lyric}\n{hiragana}\n一句时发生匹配错误', file=sys.stderr)
            return 2
    
    # 将初步匹配结果输出到文件
    notateds = get_notated(matches1, matches2, results)
    save_to_file(filename_output, notateds, translations)
    
    if manual_adjust:
        # 手动调整汉字发音的对应
        final_matches1, final_matches2 = confirm_matches(matches1, matches2)
        if final_matches1 is None and final_matches2 is None:
            print(f'错误： 在手动匹配汉字发音时出现错误', file=sys.stderr)
            return 3
        
        # 将最终匹配结果输出到文件
        final_notateds = get_notated(final_matches1, final_matches2, results)
        splited_fname = filename_output.split('.')
        filename_output_confirmed = "".join(splited_fname[:-1]) + '.confirmed' + '.' + splited_fname[-1]
        save_to_file(filename_output_confirmed, final_notateds, translations)
    return 0

# 程序入口
if __name__ == "__main__":
    ret = main()
    exit(ret)
