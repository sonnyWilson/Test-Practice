Quiz Practice App
A desktop quiz application written in Python and Tkinter for studying standard multiple-choice and multi-select exams. The app features customizable quiz parameters, shuffled options, instant scoring, and topic-by-topic weakness analysis.

Features
Custom Question Files: Load customized study materials using a simple text block format (.txt).
Multi-Select & Single-Choice Support: Handles standard single-answer items as well as multi-select questions.
Randomization: Shuffle both question presentation order and option order independently.
Flexible Quiz Sizing: Select any subset size from your question bank.
Detailed Analytics:
Score percentage breakdown with performance badges.
Weak area identification highlighting topics scoring below 70%.
Question-by-question review with full correct answer indicators and explanations.
Format for Questions
==QUESTION== TOPIC: Security Controls TEXT: Which of the following physical controls would deter someone from entering a facility? (Select TWO.)

Bollards
Guards
Barrier
Signs
ANSWER: 2,3 EXPLANATION: Guards and barriers actively prevent or deter physical unauthorized entry. ==END==

Installation & Requirements
Python: Python 3.8+
Dependencies: Standard library only (tkinter comes pre-installed with standard Python distributions on Windows and macOS).
Run the App
python quiz_app.py
