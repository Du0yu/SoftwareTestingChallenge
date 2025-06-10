from flask import Flask, render_template, request, session, redirect, url_for, jsonify, send_from_directory
import json
import random
from datetime import datetime
from pathlib import Path
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

class QuizManager:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.quizzes = {}
        self.load_all_quizzes()
        print(f"QuizManager initialized. Loaded {len(self.quizzes)} quizzes: {list(self.quizzes.keys())}")
    
    def load_all_quizzes(self):
        """Load all available quiz files"""
        print(f"Looking for quiz files in: {self.base_path}")
        print(f"Base path exists: {self.base_path.exists()}")
        
        if not self.base_path.exists():
            print(f"Creating directory: {self.base_path}")
            self.base_path.mkdir(parents=True, exist_ok=True)
        
        for i in range(1, 6):  # quiz1 to quiz5
            quiz_file = self.base_path / f'quiz{i}_questions.json'
            print(f"Checking for: {quiz_file}")
            print(f"File exists: {quiz_file.exists()}")
            
            if quiz_file.exists():
                try:
                    with open(quiz_file, 'r', encoding='utf-8') as f:
                        quiz_data = json.load(f)
                        self.quizzes[f'quiz{i}'] = {
                            'data': quiz_data,
                            'questions': quiz_data['questions'],
                            'title': quiz_data.get('title', f'软件测试题库 {i}'),
                            'file': str(quiz_file)
                        }
                        print(f"Successfully loaded {quiz_file} with {len(quiz_data['questions'])} questions")
                except Exception as e:
                    print(f"Error loading {quiz_file}: {e}")
            else:
                print(f"File not found: {quiz_file}")
    
    def get_available_quizzes(self):
        """Get list of available quizzes"""
        return {k: {'title': v['title'], 'total_questions': len(v['questions'])} 
                for k, v in self.quizzes.items()}
    
    def get_random_questions(self, quiz_id, count=10):
        if quiz_id not in self.quizzes:
            return []
        questions = self.quizzes[quiz_id]['questions']
        return random.sample(questions, min(count, len(questions)))
    
    def check_answer(self, quiz_id, question_number, user_answer):
        if quiz_id not in self.quizzes:
            return False
        questions = self.quizzes[quiz_id]['questions']
        question = next((q for q in questions if q['question_number'] == question_number), None)
        if not question:
            return False
        return user_answer.strip() == question['correct_answer'].strip()

# Initialize with absolute path to avoid path issues
try:
    quiz_manager = QuizManager('source_challenges')
    if not quiz_manager.quizzes:
        # Try alternative path
        alt_path = Path(__file__).parent / 'source_challenges'
        print(f"Trying alternative path: {alt_path}")
        quiz_manager = QuizManager(str(alt_path))
except Exception as e:
    print(f"Error initializing QuizManager: {e}")
    quiz_manager = None

@app.route('/')
def index():
    # Check if quiz manager is properly initialized
    if not quiz_manager or not quiz_manager.quizzes:
        return render_template('error.html', 
                             error_message="Quiz files could not be loaded.",
                             error_details=f"Please visit /debug for more information. Current working directory: {os.getcwd()}")
    
    # Ensure session data structure is consistent (migrate old data if needed)
    if 'attempts' not in session or not isinstance(session['attempts'], dict):
        session['attempts'] = {}
    if 'wrong_answers' not in session or not isinstance(session['wrong_answers'], dict):
        session['wrong_answers'] = {}
    if 'quiz_history' not in session or not isinstance(session['quiz_history'], dict):
        session['quiz_history'] = {}
    
    available_quizzes = quiz_manager.get_available_quizzes()
    
    # Check if any quizzes are loaded
    if not available_quizzes:
        return render_template('error.html', 
                             error_message="No quiz files found. Please ensure quiz files are in the 'source_challenges' directory.",
                             error_details=f"Looking for files in: {quiz_manager.base_path}")
    
    # Get the first available quiz as default if selected quiz doesn't exist
    first_quiz_id = list(available_quizzes.keys())[0]
    current_quiz = session.get('selected_quiz', first_quiz_id)
    
    # Validate current quiz exists, fallback to first available
    if current_quiz not in available_quizzes:
        current_quiz = first_quiz_id
        session['selected_quiz'] = current_quiz
    
    return render_template('index.html', 
                         available_quizzes=available_quizzes,
                         current_quiz=current_quiz,
                         attempts=session['attempts'].get(current_quiz, 0),
                         max_attempts=5)

@app.route('/select_quiz', methods=['POST'])
def select_quiz():
    quiz_id = request.form.get('quiz_id')
    if quiz_id in quiz_manager.get_available_quizzes():
        session['selected_quiz'] = quiz_id
    return redirect(url_for('index'))

@app.route('/start_quiz')
def start_quiz():
    available_quizzes = quiz_manager.get_available_quizzes()
    if not available_quizzes:
        return redirect(url_for('index'))
    
    first_quiz_id = list(available_quizzes.keys())[0]
    current_quiz = session.get('selected_quiz', first_quiz_id)
    
    # Validate current quiz exists
    if current_quiz not in available_quizzes:
        current_quiz = first_quiz_id
        session['selected_quiz'] = current_quiz
    
    # Ensure session data structure is consistent
    if not isinstance(session.get('attempts'), dict):
        session['attempts'] = {}
    if not isinstance(session.get('wrong_answers'), dict):
        session['wrong_answers'] = {}
    if not isinstance(session.get('quiz_history'), dict):
        session['quiz_history'] = {}
    
    # Initialize quiz-specific session data if not exists
    if current_quiz not in session['attempts']:
        session['attempts'][current_quiz] = 0
    if current_quiz not in session['wrong_answers']:
        session['wrong_answers'][current_quiz] = []
    if current_quiz not in session['quiz_history']:
        session['quiz_history'][current_quiz] = []
    
    if session['attempts'][current_quiz] >= 5:
        return redirect(url_for('quiz_complete'))
    
    # Get random questions for this quiz
    questions = quiz_manager.get_random_questions(current_quiz, 10)
    session['current_quiz_id'] = current_quiz
    session['current_quiz'] = questions
    session['current_question'] = 0
    session['current_score'] = 0
    session['current_wrong'] = []
    
    return redirect(url_for('quiz'))

@app.route('/quiz')
def quiz():
    if 'current_quiz' not in session:
        return redirect(url_for('index'))
    
    current_q_index = session.get('current_question', 0)
    questions = session['current_quiz']
    current_quiz_id = session.get('current_quiz_id', 'quiz1')
    
    if current_q_index >= len(questions):
        return redirect(url_for('quiz_result'))
    
    question = questions[current_q_index]
    
    # Safer way to get quiz title
    quiz_title = quiz_manager.quizzes.get(current_quiz_id, {}).get('title', f'Quiz {current_quiz_id}')
    
    return render_template('quiz.html', 
                         question=question,
                         question_index=current_q_index + 1,
                         total_questions=len(questions),
                         quiz_title=quiz_title)

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    if 'current_quiz' not in session:
        return redirect(url_for('index'))
    
    user_answer = request.form.get('answer')
    current_q_index = session['current_question']
    questions = session['current_quiz']
    current_question = questions[current_q_index]
    current_quiz_id = session.get('current_quiz_id', 'quiz1')
    
    # Ensure session data structure is consistent
    if not isinstance(session.get('attempts'), dict):
        session['attempts'] = {}
    if not isinstance(session.get('wrong_answers'), dict):
        session['wrong_answers'] = {}
    
    # Initialize if not exists
    if current_quiz_id not in session['attempts']:
        session['attempts'][current_quiz_id] = 0
    if current_quiz_id not in session['wrong_answers']:
        session['wrong_answers'][current_quiz_id] = []
    
    is_correct = quiz_manager.check_answer(current_quiz_id, current_question['question_number'], user_answer)
    
    if is_correct:
        session['current_score'] += 1
    else:
        wrong_answer_record = {
            'question_number': current_question['question_number'],
            'question_text': current_question['question_text'],
            'user_answer': user_answer,
            'correct_answer': current_question['correct_answer'],
            'timestamp': datetime.now().isoformat(),
            'attempt': session['attempts'][current_quiz_id] + 1,
            'quiz_id': current_quiz_id
        }
        session['current_wrong'].append(wrong_answer_record)
        
        # Add to quiz-specific wrong answers
        session['wrong_answers'][current_quiz_id].append(wrong_answer_record)
    
    session['current_question'] += 1
    return redirect(url_for('quiz'))

@app.route('/quiz_result')
def quiz_result():
    if 'current_quiz' not in session:
        return redirect(url_for('index'))
    
    score = session.get('current_score', 0)
    total = len(session['current_quiz'])
    wrong_answers = session.get('current_wrong', [])
    current_quiz_id = session.get('current_quiz_id', 'quiz1')
    
    # Ensure session data structure is consistent
    if not isinstance(session.get('attempts'), dict):
        session['attempts'] = {}
    if not isinstance(session.get('quiz_history'), dict):
        session['quiz_history'] = {}
    
    # Initialize if not exists
    if current_quiz_id not in session['attempts']:
        session['attempts'][current_quiz_id] = 0
    if current_quiz_id not in session['quiz_history']:
        session['quiz_history'][current_quiz_id] = []
    
    # Record this attempt
    session['attempts'][current_quiz_id] = session['attempts'][current_quiz_id] + 1
    
    quiz_record = {
        'attempt': session['attempts'][current_quiz_id],
        'score': score,
        'total': total,
        'percentage': round((score / total) * 100, 2),
        'wrong_count': len(wrong_answers),
        'timestamp': datetime.now().isoformat(),
        'quiz_id': current_quiz_id
    }
    
    session['quiz_history'][current_quiz_id].append(quiz_record)
    
    # Clear current quiz data
    session.pop('current_quiz', None)
    session.pop('current_question', None)
    session.pop('current_score', None)
    session.pop('current_wrong', None)
    session.pop('current_quiz_id', None)
    
    quiz_title = quiz_manager.quizzes.get(current_quiz_id, {}).get('title', f'Quiz {current_quiz_id}')
    
    return render_template('result.html', 
                         score=score,
                         total=total,
                         percentage=quiz_record['percentage'],
                         wrong_answers=wrong_answers,
                         attempt=session['attempts'][current_quiz_id],
                         max_attempts=5,
                         quiz_title=quiz_title)

@app.route('/wrong_answers')
def wrong_answers():
    current_quiz = session.get('selected_quiz', 'quiz1')
    
    # Ensure session data structure is consistent
    if not isinstance(session.get('wrong_answers'), dict):
        session['wrong_answers'] = {}
    
    wrong_answers = session['wrong_answers'].get(current_quiz, [])
    quiz_title = quiz_manager.quizzes.get(current_quiz, {}).get('title', 'Quiz')
    
    return render_template('wrong_answers.html', 
                         wrong_answers=wrong_answers,
                         quiz_title=quiz_title,
                         available_quizzes=quiz_manager.get_available_quizzes(),
                         current_quiz=current_quiz)

@app.route('/quiz_history')
def quiz_history():
    current_quiz = session.get('selected_quiz', 'quiz1')
    
    # Ensure session data structure is consistent
    if not isinstance(session.get('quiz_history'), dict):
        session['quiz_history'] = {}
    
    history = session['quiz_history'].get(current_quiz, [])
    quiz_title = quiz_manager.quizzes.get(current_quiz, {}).get('title', 'Quiz')
    
    return render_template('history.html', 
                         history=history,
                         quiz_title=quiz_title,
                         available_quizzes=quiz_manager.get_available_quizzes(),
                         current_quiz=current_quiz)

@app.route('/quiz_complete')
def quiz_complete():
    current_quiz = session.get('selected_quiz', 'quiz1')
    
    # Ensure session data structure is consistent
    if not isinstance(session.get('quiz_history'), dict):
        session['quiz_history'] = {}
    if not isinstance(session.get('wrong_answers'), dict):
        session['wrong_answers'] = {}
    
    history = session['quiz_history'].get(current_quiz, [])
    wrong_answers = session['wrong_answers'].get(current_quiz, [])
    
    # Calculate statistics
    total_questions = sum(h['total'] for h in history)
    total_correct = sum(h['score'] for h in history)
    overall_percentage = round((total_correct / total_questions) * 100, 2) if total_questions > 0 else 0
    
    # Group wrong answers by question
    wrong_by_question = {}
    for wrong in wrong_answers:
        q_num = wrong['question_number']
        if q_num not in wrong_by_question:
            wrong_by_question[q_num] = []
        wrong_by_question[q_num].append(wrong)
    
    quiz_title = quiz_manager.quizzes.get(current_quiz, {}).get('title', 'Quiz')
    
    return render_template('complete.html',
                         history=history,
                         wrong_answers=wrong_answers,
                         wrong_by_question=wrong_by_question,
                         total_questions=total_questions,
                         total_correct=total_correct,
                         overall_percentage=overall_percentage,
                         quiz_title=quiz_title)

@app.route('/reset')
def reset():
    current_quiz = session.get('selected_quiz', 'quiz1')
    
    # Ensure session data structure is consistent
    if not isinstance(session.get('attempts'), dict):
        session['attempts'] = {}
    if not isinstance(session.get('wrong_answers'), dict):
        session['wrong_answers'] = {}
    if not isinstance(session.get('quiz_history'), dict):
        session['quiz_history'] = {}
    
    # Reset only current quiz data
    if current_quiz in session['attempts']:
        session['attempts'][current_quiz] = 0
    if current_quiz in session['wrong_answers']:
        session['wrong_answers'][current_quiz] = []
    if current_quiz in session['quiz_history']:
        session['quiz_history'][current_quiz] = []
    
    return redirect(url_for('index'))

@app.route('/reset_all')
def reset_all():
    session.clear()
    return redirect(url_for('index'))

@app.route('/api/stats')
def api_stats():
    current_quiz = session.get('selected_quiz', 'quiz1')
    
    # Ensure session data structure is consistent
    if not isinstance(session.get('attempts'), dict):
        session['attempts'] = {}
    if not isinstance(session.get('wrong_answers'), dict):
        session['wrong_answers'] = {}
    if not isinstance(session.get('quiz_history'), dict):
        session['quiz_history'] = {}
    
    return jsonify({
        'current_quiz': current_quiz,
        'attempts': session['attempts'].get(current_quiz, 0),
        'wrong_answers_count': len(session['wrong_answers'].get(current_quiz, [])),
        'quiz_history': session['quiz_history'].get(current_quiz, []),
        'all_attempts': session['attempts'],
        'available_quizzes': quiz_manager.get_available_quizzes()
    })

# Add a route to check quiz loading status
@app.route('/debug')
def debug():
    if quiz_manager:
        return jsonify({
            'base_path': str(quiz_manager.base_path),
            'base_path_exists': quiz_manager.base_path.exists(),
            'loaded_quizzes': list(quiz_manager.quizzes.keys()),
            'quiz_details': {k: {'title': v['title'], 'questions_count': len(v['questions'])} 
                           for k, v in quiz_manager.quizzes.items()}
        })
    else:
        return jsonify({'error': 'QuizManager not initialized'})

@app.route('/quiz_images/<path:filename>')
def quiz_images(filename):
    """Serve images from the source_challenges/images directory"""
    images_dir = Path(__file__).parent / 'source_challenges' / 'images'
    return send_from_directory(images_dir, filename)

@app.route('/debug_images')
def debug_images():
    """Debug route to check image availability"""
    # Check both static and source_challenges directories
    static_dir = Path(app.static_folder) if app.static_folder else Path(__file__).parent / 'static'
    static_images_dir = static_dir / 'images'
    source_images_dir = Path(__file__).parent / 'source_challenges' / 'images'
    
    image_info = {
        'static_images_dir': str(static_images_dir),
        'static_images_exists': static_images_dir.exists(),
        'source_images_dir': str(source_images_dir),
        'source_images_exists': source_images_dir.exists(),
        'static_images': [],
        'source_images': []
    }
    
    # Check static images
    if static_images_dir.exists():
        for img_file in static_images_dir.glob('*'):
            if img_file.is_file() and img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                image_info['static_images'].append({
                    'filename': img_file.name,
                    'path': f'images/{img_file.name}',
                    'size': img_file.stat().st_size
                })
    
    # Check source images
    if source_images_dir.exists():
        for img_file in source_images_dir.glob('*'):
            if img_file.is_file() and img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                image_info['source_images'].append({
                    'filename': img_file.name,
                    'path': f'quiz_images/{img_file.name}',
                    'size': img_file.stat().st_size
                })
    
    # Check which quiz questions need images
    image_questions = []
    if quiz_manager:
        for quiz_id, quiz_data in quiz_manager.quizzes.items():
            for q in quiz_data['questions']:
                if q.get('has_image', False):
                    # Fix the image path
                    image_src = q.get('image_src', '')
                    if image_src:
                        # Convert backslashes to forward slashes and remove 'images\' prefix
                        clean_filename = image_src.replace('\\', '/').replace('images/', '').replace('images\\', '')
                        image_questions.append({
                            'quiz_id': quiz_id,
                            'question_number': q['question_number'],
                            'original_image_src': image_src,
                            'clean_filename': clean_filename,
                            'new_url': f'/quiz_images/{clean_filename}',
                            'image_alt': q.get('image_alt', 'No alt text')
                        })
    
    image_info['questions_with_images'] = image_questions
    
    return jsonify(image_info)

