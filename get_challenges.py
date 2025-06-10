import json
import re
from bs4 import BeautifulSoup
from pathlib import Path

def parse_quiz_html(html_file_path, output_json_path):
    """
    解析HTML文件中的测试题目并保存到JSON文件
    
    Args:
        html_file_path: HTML文件路径
        output_json_path: 输出JSON文件路径
    """
    
    # 读取HTML文件
    with open(html_file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 查找所有题目div
    question_divs = soup.find_all('div')
    
    questions = []
    
    for div in question_divs:
        # 查找题目标题
        h3 = div.find('h3')
        if not h3 or not h3.text.startswith('试题'):
            continue
            
        question_data = {}
        
        # 提取题目编号
        question_number = re.search(r'试题 (\d+)', h3.text)
        if question_number:
            question_data['question_number'] = int(question_number.group(1))
        
        # 提取题目内容
        question_text = ""
        paragraphs = div.find_all('p')
        
        for i, p in enumerate(paragraphs):
            if '选择一项：' in p.text:
                break
            if '正确答案是：' in p.text:
                break
            if i == 0:  # 第一个p标签通常是题目描述
                question_text = p.get_text(strip=True)
                break
        
        question_data['question_text'] = question_text
        
        # 提取选项
        options = []
        ul = div.find('ul')
        if ul:
            li_elements = ul.find_all('li')
            for li in li_elements:
                option_text = li.get_text(strip=True)
                if option_text:  # 确保选项不为空
                    options.append(option_text)
        
        question_data['options'] = options
        
        # 提取正确答案
        correct_answer = ""
        for p in paragraphs:
            if '正确答案是：' in p.text:
                correct_answer = p.text.replace('正确答案是：', '').strip()
                break
        
        question_data['correct_answer'] = correct_answer
        
        # 检查是否包含图片
        img = div.find('img')
        if img:
            question_data['has_image'] = True
            question_data['image_src'] = img.get('src', '')
            question_data['image_alt'] = img.get('alt', '')
        else:
            question_data['has_image'] = False
        
        # 只添加有效的题目（至少包含题目文本）
        if question_data.get('question_text'):
            questions.append(question_data)
    
    # 保存到JSON文件
    output_data = {
        'total_questions': len(questions),
        'questions': questions
    }
    
    with open(output_json_path, 'w', encoding='utf-8') as json_file:
        json.dump(output_data, json_file, ensure_ascii=False, indent=2)
    
    print(f"成功解析 {len(questions)} 道题目，已保存到 {output_json_path}")
    return output_data

def main():
    # 定义文件路径
    html_file = r"C:\Users\Duoyu\Documents\Code\SoftwareTestingChallenge\source_challenges\simpread-测验五：综合应用：答题回顾  砺儒云课堂.html"
    json_file = r"c:\Users\Duoyu\Documents\Code\SoftwareTestingChallenge\quiz5_questions.json"
    
    # 确保输出目录存在
    Path(json_file).parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # 解析HTML并保存到JSON
        result = parse_quiz_html(html_file, json_file)
        
        # 打印解析结果概览
        print(f"\n解析完成！")
        print(f"总题目数: {result['total_questions']}")
        
        # 显示前3题的概览
        for i, question in enumerate(result['questions'][:3]):
            print(f"\n题目 {question['question_number']}:")
            print(f"  内容: {question['question_text'][:50]}...")
            print(f"  选项数: {len(question['options'])}")
            print(f"  正确答案: {question['correct_answer']}")
            print(f"  包含图片: {question['has_image']}")
            
    except FileNotFoundError:
        print(f"错误：找不到HTML文件 {html_file}")
    except Exception as e:
        print(f"解析过程中出现错误: {str(e)}")

if __name__ == "__main__":
    main()