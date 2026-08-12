#!/usr/bin/env python3
"""
Quiz Practice App
=================
Randomized questions with grading and weak area analysis.

Question file format:
    ==QUESTION==
    TOPIC: Certificate Management
    TEXT: What should the admin do first?

    1. Option A
    2. Option B
    3. Option C
    4. Option D

    ANSWER: 3
    EXPLANATION: Because option C is correct...
    ==END==

For multi-select, add "(Select TWO)" to TEXT and use "ANSWER: 2,3"
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import random
import re
import copy
from collections import defaultdict

# ─────────────────────────────────────────────
# BUILT-IN SAMPLE QUESTIONS
# ─────────────────────────────────────────────
SAMPLE_QUESTIONS = """==QUESTION==
TOPIC: Certificate Management
TEXT: A user has reported to the security team that they left their laptop logged in and unattended. This laptop has a certificate that they use to access the payroll application. What should the security administrator do first?

1. Revoke the certificate for the payroll application
2. Get the user to make a statement
3. Add the certificate to the CRL
4. Report the user to their line manager

ANSWER: 3
EXPLANATION: The certificate must be added to the Certificate Revocation List (CRL). This invalidates it and prevents its use. As this is for a payroll application, it must be done immediately. Option A is incorrect — you cannot revoke a certificate for a single application; it is revoked entirely. Option B is not the main priority; the incident must be handled first. Option D is also secondary to resolving the security incident.
==END==

==QUESTION==
TOPIC: Virtualization Security
TEXT: After some routine checks of a company's virtual network, three rogue virtual machines were found connected to the network. These machines were overutilizing resources. What should be done to prevent this from happening again? (Select TWO.)

1. Implement manual procedures for VM provisioning, utilization, and decommissioning
2. Craft explicit guidelines for the provisioning, utilization, and decommissioning of Virtual Machines
3. Employ automated solutions to instantiate VMs using predefined templates and established configurations
4. Avoid using predefined templates and automated tools to adapt to dynamic workload requirements

ANSWER: 2,3
EXPLANATION: The attack described is VM sprawl. Creating a formal policy on resource allocation combined with automated provisioning will prevent it. The policy stops unmanaged VMs from being deployed; automation reduces human error. Option A is incorrect because manual procedures are prone to human error. Option D is incorrect because predefined templates streamline the process and reduce configuration errors.
==END==

==QUESTION==
TOPIC: Mobile Device Security
TEXT: The CEO of a company is going on a trip and will be listening to music on their company phone using Bluetooth earbuds. What security practice should you advise them to follow after each listening session? (Select the MOST secure option.)

1. Turn off the phone's Bluetooth
2. Turn off the phone's Wi-Fi
3. Clean the earbuds
4. Change the Bluetooth username and password

ANSWER: 1
EXPLANATION: Earbuds use Bluetooth, which is insecure because a malicious actor can easily pair to the host device. Bluetooth should be turned off when not in use. Option B is incorrect — earbuds do not use Wi-Fi. Option C is incorrect — cleaning earbuds has no effect on phone security. Option D is incorrect — Bluetooth devices pair using a PIN, not a traditional username and password.
==END==
"""


# ─────────────────────────────────────────────
# PARSER
# ─────────────────────────────────────────────
def parse_questions(text: str) -> list:
    """Parse questions from ==QUESTION== ... ==END== blocks."""
    questions = []
    for block in re.split(r'==END==', text, flags=re.IGNORECASE):
        block = re.sub(r'==QUESTION==\s*', '', block.strip(), flags=re.IGNORECASE).strip()
        if not block:
            continue

        q = {
            'topic':       'General',
            'text':        '',
            'options':     [],
            'answers':     [],   # 0-indexed
            'explanation': '',
            'multiple':    False,
        }

        lines = block.splitlines()
        i = 0

        if i < len(lines) and lines[i].upper().startswith('TOPIC:'):
            q['topic'] = lines[i].split(':', 1)[1].strip()
            i += 1

        while i < len(lines) and not lines[i].strip():
            i += 1

        text_parts = []
        if i < len(lines) and lines[i].upper().startswith('TEXT:'):
            text_parts.append(lines[i].split(':', 1)[1].strip())
            i += 1

        while i < len(lines):
            s = lines[i].strip()
            if re.match(r'^\d+[.)]\s', s) or s.upper().startswith(('ANSWER:', 'EXPLANATION:')):
                break
            text_parts.append(lines[i])
            i += 1

        q['text'] = '\n'.join(text_parts).strip()
        if re.search(r'select\s+(two|three|\d+|all that apply)', q['text'], re.IGNORECASE):
            q['multiple'] = True

        while i < len(lines) and re.match(r'^\s*\d+[.)]\s', lines[i].strip()):
            m = re.match(r'^\s*\d+[.)]\s+(.*)', lines[i].strip())
            if m:
                q['options'].append(m.group(1).strip())
            i += 1

        while i < len(lines) and not lines[i].strip():
            i += 1

        if i < len(lines) and lines[i].upper().startswith('ANSWER:'):
            for part in lines[i].split(':', 1)[1].strip().split(','):
                part = part.strip()
                if part.isdigit():
                    q['answers'].append(int(part) - 1)
            i += 1

        while i < len(lines) and not lines[i].strip():
            i += 1

        if i < len(lines) and lines[i].upper().startswith('EXPLANATION:'):
            exp = [lines[i].split(':', 1)[1].strip()]
            i += 1
            while i < len(lines):
                exp.append(lines[i])
                i += 1
            q['explanation'] = '\n'.join(exp).strip()

        if q['text'] and q['options'] and q['answers']:
            questions.append(q)

    return questions


# ─────────────────────────────────────────────
# COLOUR PALETTE
# ─────────────────────────────────────────────
BG      = '#0f172a'
CARD    = '#1e293b'
CARD2   = '#263347'
TEXT    = '#cbd5e1'
WHITE   = '#f1f5f9'
MUTED   = '#64748b'
ACCENT  = '#6366f1'
ACCENT2 = '#818cf8'
SUCCESS = '#22c55e'
DANGER  = '#ef4444'
WARNING = '#f59e0b'
BORDER  = '#334155'
EXP_BG  = '#0c1a2c'


# ─────────────────────────────────────────────
# APPLICATION
# ─────────────────────────────────────────────
class QuizApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Quiz Practice App')
        self.geometry('980x700')
        self.minsize(780, 560)
        self.configure(bg=BG)

        self.questions:      list = []
        self.quiz_questions: list = []
        self.current_index:  int  = 0
        self.user_answers:   dict = {}   # idx -> set of 0-indexed picks
        self._active_canvas       = None

        ttk.Style(self).configure('TProgressbar',
                                  background=ACCENT, troughcolor=BORDER, thickness=5)
        self._screen_welcome()

    # ── Widget helpers ──────────────────────────────────────

    def _clear(self):
        if self._active_canvas:
            try:
                self._active_canvas.unbind_all('<MouseWheel>')
            except Exception:
                pass
            self._active_canvas = None
        for w in self.winfo_children():
            w.destroy()

    def _btn(self, parent, text, cmd, color=ACCENT, fg=WHITE, px=22, py=10):
        b = tk.Button(parent, text=text, command=cmd, bg=color, fg=fg,
                      font=('Segoe UI', 11, 'bold'), relief='flat',
                      cursor='hand2', padx=px, pady=py,
                      activebackground=self._shift(color, 28),
                      activeforeground=fg, bd=0)
        b.bind('<Enter>', lambda e, b=b, c=color: b.config(bg=self._shift(c, 28)))
        b.bind('<Leave>', lambda e, b=b, c=color: b.config(bg=c))
        return b

    @staticmethod
    def _shift(h, a):
        h = h.lstrip('#')
        r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:], 16)
        return f'#{min(255,r+a):02x}{min(255,g+a):02x}{min(255,b+a):02x}'

    def _scrollable(self, parent):
        """Return (canvas, inner_frame) with mouse-wheel support."""
        c = tk.Canvas(parent, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(parent, orient='vertical', command=c.yview,
                          bg=BORDER, troughcolor=BG)
        c.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        c.pack(side='left', fill='both', expand=True)
        inner = tk.Frame(c, bg=BG)
        win = c.create_window((0, 0), window=inner, anchor='nw')
        inner.bind('<Configure>', lambda e: c.configure(scrollregion=c.bbox('all')))
        c.bind('<Configure>', lambda e: c.itemconfig(win, width=e.width))
        c.bind_all('<MouseWheel>',
                   lambda e: c.yview_scroll(int(-1 * e.delta / 120), 'units'))
        self._active_canvas = c
        return c, inner

    # ── SCREEN: Welcome ─────────────────────────────────────

    def _screen_welcome(self):
        self._clear()

        center = tk.Frame(self, bg=BG)
        center.place(relx=0.5, rely=0.44, anchor='center')

        tk.Label(center, text='📚', font=('Segoe UI', 52), bg=BG).pack()
        tk.Label(center, text='Quiz Practice App',
                 font=('Segoe UI', 28, 'bold'), bg=BG, fg=WHITE).pack(pady=(4, 2))
        tk.Label(center,
                 text='Randomized questions  ·  Instant grading  ·  Weak area analysis',
                 font=('Segoe UI', 12), bg=BG, fg=MUTED).pack(pady=(0, 28))

        row = tk.Frame(center, bg=BG)
        row.pack()
        self._btn(row, '▶  Use Sample Questions', self._load_sample).grid(row=0, column=0, padx=6)
        self._btn(row, '📂  Load Questions File',
                  self._load_file, color=CARD).grid(row=0, column=1, padx=6)

        hint = tk.Frame(self, bg=CARD, padx=24, pady=16)
        hint.place(relx=0.5, rely=0.89, anchor='center')
        tk.Label(hint, text='Question file format  (.txt)',
                 font=('Segoe UI', 9, 'bold'), bg=CARD, fg=MUTED).pack(anchor='w')
        tk.Label(hint, justify='left', bg=CARD, fg=MUTED, font=('Courier New', 9),
                 text=("==QUESTION==\n"
                       "TOPIC: Certificate Management\n"
                       "TEXT: What should the admin do first?\n\n"
                       "1. Option A\n2. Option B\n3. Option C\n\n"
                       "ANSWER: 2          ← use  2,3  for multi-select\n"
                       "EXPLANATION: Because...\n"
                       "==END==")).pack(anchor='w')

    def _load_sample(self):
        qs = parse_questions(SAMPLE_QUESTIONS)
        if not qs:
            messagebox.showerror('Error', 'Could not parse sample questions.')
            return
        self.questions = qs
        self._screen_setup()

    def _load_file(self):
        path = filedialog.askopenfilename(
            title='Select Questions File',
            filetypes=[('Text files', '*.txt'), ('All files', '*.*')])
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                qs = parse_questions(f.read())
            if not qs:
                messagebox.showerror('Parse Error',
                    'No valid questions found.\n\n'
                    'Ensure each question uses the\n==QUESTION== … ==END== format.')
                return
            self.questions = qs
            self._screen_setup()
        except Exception as exc:
            messagebox.showerror('Error', f'Failed to read file:\n{exc}')

    # ── SCREEN: Setup ────────────────────────────────────────

    def _screen_setup(self):
        self._clear()

        center = tk.Frame(self, bg=BG)
        center.place(relx=0.5, rely=0.5, anchor='center')

        tk.Label(center, text='Quiz Settings',
                 font=('Segoe UI', 22, 'bold'), bg=BG, fg=WHITE).pack(pady=(0, 4))
        tk.Label(center, text=f'{len(self.questions)} questions loaded',
                 font=('Segoe UI', 12), bg=BG, fg=MUTED).pack(pady=(0, 22))

        card = tk.Frame(center, bg=CARD, padx=34, pady=28)
        card.pack()

        self._v_rand_q = tk.BooleanVar(value=True)
        self._v_rand_a = tk.BooleanVar(value=False)

        for r, (lbl, var) in enumerate([
            ('Randomize question order', self._v_rand_q),
            ('Randomize answer order',   self._v_rand_a),
        ]):
            tk.Label(card, text=lbl, font=('Segoe UI', 12),
                     bg=CARD, fg=TEXT).grid(row=r, column=0, sticky='w', pady=8)
            tk.Checkbutton(card, variable=var, bg=CARD, activebackground=CARD,
                           selectcolor=BORDER, fg=TEXT, cursor='hand2',
                           relief='flat').grid(row=r, column=1, sticky='e', padx=(42, 0))

        tk.Frame(card, bg=BORDER, height=1).grid(
            row=2, column=0, columnspan=2, sticky='ew', pady=(12, 8))

        tk.Label(card, text='Number of questions', font=('Segoe UI', 12),
                 bg=CARD, fg=TEXT).grid(row=3, column=0, sticky='w')
        self._v_n = tk.IntVar(value=len(self.questions))
        n_row = tk.Frame(card, bg=CARD)
        n_row.grid(row=4, column=0, columnspan=2, sticky='ew', pady=(4, 0))
        tk.Scale(n_row, from_=1, to=len(self.questions), orient='horizontal',
                 variable=self._v_n, length=224, bg=CARD, fg=TEXT,
                 troughcolor=BORDER, highlightthickness=0,
                 sliderrelief='flat', activebackground=ACCENT).pack(side='left')
        tk.Label(n_row, textvariable=self._v_n, font=('Segoe UI', 13, 'bold'),
                 bg=CARD, fg=ACCENT, width=3).pack(side='left', padx=8)

        btns = tk.Frame(center, bg=BG)
        btns.pack(pady=(22, 0))
        self._btn(btns, '← Back', self._screen_welcome, color=BORDER).pack(side='left', padx=6)
        self._btn(btns, 'Start Quiz ▶', self._begin_quiz).pack(side='left', padx=6)

    def _begin_quiz(self):
        pool = list(self.questions)
        if self._v_rand_q.get():
            random.shuffle(pool)
        n = self._v_n.get()
        self.quiz_questions = [copy.deepcopy(q) for q in pool[:n]]

        if self._v_rand_a.get():
            for q in self.quiz_questions:
                indexed = list(enumerate(q['options']))
                random.shuffle(indexed)
                q['options'] = [t for _, t in indexed]
                old_to_new = {old: new for new, (old, _) in enumerate(indexed)}
                q['answers'] = sorted(old_to_new[a] for a in q['answers'])

        self.current_index = 0
        self.user_answers  = {}
        self._screen_quiz()

    # ── SCREEN: Quiz ─────────────────────────────────────────

    def _screen_quiz(self):
        self._clear()

        bar = tk.Frame(self, bg=CARD, padx=20, pady=12)
        bar.pack(fill='x')
        tk.Label(bar, text='Quiz Practice',
                 font=('Segoe UI', 12, 'bold'), bg=CARD, fg=WHITE).pack(side='left')
        self._prog_lbl = tk.Label(bar, text='', font=('Segoe UI', 11), bg=CARD, fg=MUTED)
        self._prog_lbl.pack(side='right')

        self._pbar_var = tk.DoubleVar()
        ttk.Progressbar(self, variable=self._pbar_var,
                        maximum=len(self.quiz_questions)).pack(fill='x')

        wrapper = tk.Frame(self, bg=BG)
        wrapper.pack(fill='both', expand=True)
        self._q_canvas, self._q_inner = self._scrollable(wrapper)

        self._render_question()

    def _render_question(self):
        for w in self._q_inner.winfo_children():
            w.destroy()

        idx   = self.current_index
        q     = self.quiz_questions[idx]
        total = len(self.quiz_questions)

        self._prog_lbl.config(text=f'Question {idx + 1} of {total}')
        self._pbar_var.set(idx + 1)

        pad = tk.Frame(self._q_inner, bg=BG)
        pad.pack(fill='both', padx=44, pady=22)

        tk.Label(pad, text=f'📌  {q["topic"]}',
                 font=('Segoe UI', 10, 'bold'), bg=BG, fg=ACCENT).pack(anchor='w', pady=(0, 8))

        qcard = tk.Frame(pad, bg=CARD, padx=24, pady=20)
        qcard.pack(fill='x')
        note = '  ·  Select all that apply' if q['multiple'] else ''
        tk.Label(qcard, text=f'Question {idx + 1}{note}',
                 font=('Segoe UI', 10), bg=CARD, fg=MUTED).pack(anchor='w')
        tk.Label(qcard, text=q['text'], font=('Segoe UI', 12),
                 bg=CARD, fg=WHITE, wraplength=840, justify='left').pack(anchor='w', pady=(8, 0))

        saved = self.user_answers.get(idx, set())

        if q['multiple']:
            self._check_vars = [tk.BooleanVar(value=(i in saved)) for i in range(len(q['options']))]
        else:
            self._radio_var = tk.IntVar(value=next(iter(saved), -1))

        opts = tk.Frame(pad, bg=BG)
        opts.pack(fill='x', pady=(14, 0))
        for oi, txt in enumerate(q['options']):
            self._make_option(opts, oi, txt, q['multiple'])

        nav = tk.Frame(pad, bg=BG)
        nav.pack(fill='x', pady=(22, 10))

        if idx > 0:
            self._btn(nav, '← Previous', self._go_prev, color=BORDER).pack(side='left')

        if idx < total - 1:
            self._btn(nav, 'Next →', self._go_next).pack(side='right')
        else:
            self._btn(nav, '✓  Submit Quiz', self._submit, color=SUCCESS).pack(side='right')

        self._q_canvas.yview_moveto(0)

    def _make_option(self, parent, oi, txt, multiple):
        frame = tk.Frame(parent, bg=CARD, padx=16, pady=11, cursor='hand2')
        frame.pack(fill='x', pady=3)
        label = f'{"ABCD"[oi]}.  {txt}'

        if multiple:
            var = self._check_vars[oi]
            w = tk.Checkbutton(frame, text=label, variable=var,
                               font=('Segoe UI', 11), bg=CARD, fg=TEXT,
                               activebackground=CARD, activeforeground=WHITE,
                               selectcolor=BORDER, cursor='hand2',
                               wraplength=840, justify='left', anchor='w')
            w.pack(anchor='w', fill='x')
            frame.bind('<Button-1>', lambda e, v=var: v.set(not v.get()))
        else:
            w = tk.Radiobutton(frame, text=label, variable=self._radio_var, value=oi,
                               font=('Segoe UI', 11), bg=CARD, fg=TEXT,
                               activebackground=CARD, activeforeground=WHITE,
                               selectcolor=BORDER, cursor='hand2',
                               wraplength=840, justify='left', anchor='w')
            w.pack(anchor='w', fill='x')
            frame.bind('<Button-1>', lambda e, rv=self._radio_var, val=oi: rv.set(val))

        def on(e, f=frame, wgt=w):  f.config(bg=CARD2); wgt.config(bg=CARD2)
        def off(e, f=frame, wgt=w): f.config(bg=CARD);  wgt.config(bg=CARD)
        frame.bind('<Enter>', on);  frame.bind('<Leave>', off)

    def _save_answer(self):
        idx = self.current_index
        q   = self.quiz_questions[idx]
        if q['multiple']:
            sel = {i for i, v in enumerate(self._check_vars) if v.get()}
        else:
            val = self._radio_var.get()
            sel = {val} if val >= 0 else set()
        self.user_answers[idx] = sel

    def _go_prev(self):
        self._save_answer(); self.current_index -= 1; self._render_question()

    def _go_next(self):
        self._save_answer(); self.current_index += 1; self._render_question()

    def _submit(self):
        self._save_answer()
        unanswered = [i + 1 for i in range(len(self.quiz_questions))
                      if not self.user_answers.get(i)]
        if unanswered:
            if not messagebox.askyesno(
                    'Unanswered Questions',
                    f'{len(unanswered)} question(s) still unanswered:\n'
                    f'Q{", Q".join(map(str, unanswered))}\n\nSubmit anyway?'):
                return
        self._screen_results()

    # ── SCREEN: Results ──────────────────────────────────────

    def _screen_results(self):
        self._clear()

        results = []
        for i, q in enumerate(self.quiz_questions):
            user = self.user_answers.get(i, set())
            cset = set(q['answers'])
            results.append({'q': q, 'user': user,
                            'correct': user == cset, 'cset': cset})

        total = len(results)
        score = sum(1 for r in results if r['correct'])
        pct   = score / total * 100 if total else 0

        topic_stats: dict = defaultdict(lambda: {'c': 0, 't': 0})
        for r in results:
            t = r['q']['topic']
            topic_stats[t]['t'] += 1
            if r['correct']:
                topic_stats[t]['c'] += 1

        # Top bar
        bar = tk.Frame(self, bg=CARD, padx=20, pady=12)
        bar.pack(fill='x')
        tk.Label(bar, text='Results', font=('Segoe UI', 13, 'bold'),
                 bg=CARD, fg=WHITE).pack(side='left')
        self._btn(bar, '🔄  Retake', self._screen_setup,
                  color=BORDER, px=14, py=7).pack(side='right', padx=4)
        self._btn(bar, '🏠  Home', self._screen_welcome,
                  color=BORDER, px=14, py=7).pack(side='right', padx=4)

        wrapper = tk.Frame(self, bg=BG)
        wrapper.pack(fill='both', expand=True)
        _, inner = self._scrollable(wrapper)
        pad = tk.Frame(inner, bg=BG)
        pad.pack(fill='both', padx=44, pady=22)

        # Score hero
        gc = SUCCESS if pct >= 70 else WARNING if pct >= 50 else DANGER
        icon  = '🏆' if pct >= 90 else '✅' if pct >= 70 else '⚠️' if pct >= 50 else '❌'
        grade = ('Excellent!' if pct >= 90 else 'Passed' if pct >= 70
                 else 'Borderline' if pct >= 50 else 'Needs Work')

        hero = tk.Frame(pad, bg=CARD, padx=30, pady=24)
        hero.pack(fill='x', pady=(0, 18))
        tk.Label(hero, text=icon, font=('Segoe UI', 44), bg=CARD).grid(
            row=0, column=0, rowspan=3, padx=(0, 28))
        tk.Label(hero, text=f'{pct:.0f}%', font=('Segoe UI', 42, 'bold'),
                 bg=CARD, fg=gc).grid(row=0, column=1, sticky='sw')
        tk.Label(hero, text=f'{score} / {total} correct',
                 font=('Segoe UI', 14), bg=CARD, fg=MUTED).grid(row=1, column=1, sticky='nw')
        tk.Label(hero, text=grade, font=('Segoe UI', 12, 'bold'),
                 bg=CARD, fg=gc).grid(row=2, column=1, sticky='nw', pady=(2, 0))

        # Topic performance
        tk.Label(pad, text='Performance by Topic',
                 font=('Segoe UI', 14, 'bold'), bg=BG, fg=WHITE).pack(anchor='w', pady=(0, 8))

        for topic, st in sorted(topic_stats.items()):
            tp = st['c'] / st['t'] * 100
            tc = SUCCESS if tp >= 70 else WARNING if tp >= 50 else DANGER
            weak = tp < 70

            tc_card = tk.Frame(pad, bg=CARD, padx=20, pady=12)
            tc_card.pack(fill='x', pady=3)

            left = tk.Frame(tc_card, bg=CARD)
            left.pack(side='left', fill='x', expand=True)

            hl = tk.Frame(left, bg=CARD)
            hl.pack(fill='x')
            tk.Label(hl, text=topic, font=('Segoe UI', 11, 'bold'),
                     bg=CARD, fg=WHITE).pack(side='left')
            if weak:
                tk.Label(hl, text='  ⚠ Needs Improvement',
                         font=('Segoe UI', 10), bg=CARD, fg=WARNING).pack(side='left')
            tk.Label(tc_card, text=f'{st["c"]}/{st["t"]}  ({tp:.0f}%)',
                     font=('Segoe UI', 12, 'bold'), bg=CARD, fg=tc).pack(side='right')

            pb = tk.Canvas(left, bg=BORDER, height=5, highlightthickness=0)
            pb.pack(fill='x', pady=(8, 0))
            pb.update_idletasks()
            w = max(pb.winfo_width(), 1)
            pb.create_rectangle(0, 0, int(w * tp / 100), 5, fill=tc, outline='')

        # Weak area callout
        weak_topics = [t for t, st in topic_stats.items()
                       if st['c'] / st['t'] * 100 < 70]
        if weak_topics:
            ws = tk.Frame(pad, bg='#1c1200', padx=20, pady=14)
            ws.pack(fill='x', pady=(14, 0))
            tk.Label(ws, text='⚠  Focus Areas for Review',
                     font=('Segoe UI', 11, 'bold'), bg='#1c1200', fg=WARNING).pack(anchor='w')
            for t in weak_topics:
                st = topic_stats[t]
                tp = st['c'] / st['t'] * 100
                tk.Label(ws, text=f'  • {t}  —  {tp:.0f}% ({st["c"]}/{st["t"]})',
                         font=('Segoe UI', 11), bg='#1c1200', fg=TEXT).pack(anchor='w', pady=1)

        # Question-by-question review
        tk.Label(pad, text='Question Review',
                 font=('Segoe UI', 14, 'bold'), bg=BG, fg=WHITE).pack(anchor='w', pady=(20, 8))

        for qi, r in enumerate(results):
            q  = r['q']
            sc = SUCCESS if r['correct'] else DANGER
            si = '✓' if r['correct'] else '✗'

            qcard = tk.Frame(pad, bg=CARD, padx=20, pady=16)
            qcard.pack(fill='x', pady=4)

            hdr = tk.Frame(qcard, bg=CARD)
            hdr.pack(fill='x')
            tk.Label(hdr, text=f'{si}  Q{qi + 1}',
                     font=('Segoe UI', 12, 'bold'), bg=CARD, fg=sc).pack(side='left')
            tk.Label(hdr, text=q['topic'],
                     font=('Segoe UI', 10), bg=CARD, fg=ACCENT).pack(side='right')

            tk.Label(qcard, text=q['text'], font=('Segoe UI', 11),
                     bg=CARD, fg=WHITE, wraplength=880, justify='left').pack(
                anchor='w', pady=(8, 10))

            for oi, opt in enumerate(q['options']):
                is_correct = oi in r['cset']
                was_chosen = oi in r['user']
                if   is_correct and     was_chosen: marker, fg = '✓  ', SUCCESS
                elif is_correct and not was_chosen: marker, fg = '→  ', WARNING
                elif not is_correct and was_chosen: marker, fg = '✗  ', DANGER
                else:                               marker, fg = '   ', MUTED

                tk.Label(qcard, text=f'{marker}{"ABCD"[oi]}. {opt}',
                         font=('Segoe UI', 10), bg=CARD, fg=fg,
                         wraplength=880, justify='left').pack(
                    anchor='w', padx=12, pady=1)

            if q['explanation']:
                exp = tk.Frame(qcard, bg=EXP_BG, padx=14, pady=10)
                exp.pack(fill='x', pady=(10, 0))
                tk.Label(exp, text='💡  Explanation',
                         font=('Segoe UI', 10, 'bold'), bg=EXP_BG, fg=ACCENT2).pack(anchor='w')
                tk.Label(exp, text=q['explanation'], font=('Segoe UI', 10),
                         bg=EXP_BG, fg=TEXT, wraplength=880, justify='left').pack(
                    anchor='w', pady=(5, 0))

        tk.Frame(pad, bg=BG, height=40).pack()


if __name__ == '__main__':
    QuizApp().mainloop()
