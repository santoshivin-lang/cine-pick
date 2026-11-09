"""Run with python -m unittest -v test_regressions (no TMDB credentials needed)."""
import ast
import re
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
APP = (ROOT / 'app.py').read_text(encoding='utf-8')
HYBRID = (ROOT / 'hybrid.py').read_text(encoding='utf-8')


def functions(source, names, namespace):
    tree = ast.parse(source)
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    for node in nodes:
        node.decorator_list = []
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<functions>', 'exec'), namespace)
    return namespace


class State(dict):
    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


class UI:
    def __init__(self):
        self.session_state = State()
        self.clicked = set()
        self.messages = []
        self.inputs = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def columns(self, widths):
        return [self] * (widths if isinstance(widths, int) else len(widths))

    def button(self, label, **kwargs):
        return kwargs.get('key', label) in self.clicked

    def selectbox(self, label, options, **kwargs):
        self.inputs[label] = kwargs
        return options[kwargs.get('index', 0)]

    def number_input(self, label, **kwargs):
        self.inputs[label] = kwargs
        return kwargs['value']

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.messages.append((name, args))
        return record


class Regressions(unittest.TestCase):
    def test_syntax(self):
        compile(APP, 'app.py', 'exec')
        compile(HYBRID, 'hybrid.py', 'exec')

    def test_title_normalization(self):
        normalize = functions(APP, {'normalize_movie_title'}, {'re': re})['normalize_movie_title']
        cases = {
            'American Tail, An (1986)': 'An American Tail',
            'American Tail: Fievel Goes West, An (1991)': 'An American Tail: Fievel Goes West',
            "Bug's Life, A (1998)": "A Bug's Life",
            'Lion King, The (1994)': 'The Lion King',
            'Toy Story (1995)': 'Toy Story',
            'Example, Another Story (1995)': 'Example, Another Story',
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                self.assertEqual(normalize(title), expected)

    def test_both_tmdb_lookups_use_normalization(self):
        tree = ast.parse(APP)
        for name in ('get_movie_poster', 'get_movie_details'):
            fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
            self.assertTrue(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                                and n.func.id == 'normalize_movie_title' for n in ast.walk(fn)))

    def test_search_counts_all_matches_but_displays_twelve(self):
        ui = UI()
        movies = pd.DataFrame({'title': ['The movie ' + str(i) for i in range(20)]})
        code = APP.split('# ---------------- SEARCH MOVIES ----------------')[1].split('# ---------------- BROWSE BY GENRE ----------------')[0]
        ui.text_input = lambda *a, **k: 'the'
        exec(code, {'st': ui, 'movies': movies, 'get_movie_poster': lambda t: None,
                    'poster_urls': {}, 'html': __import__('html')})
        captions = [args[0] for name, args in ui.messages if name == 'caption']
        self.assertIn('Found 20 matching movies (showing up to 12).', captions)
        self.assertEqual(sum(name == 'markdown' for name, _ in ui.messages), 12)

    def test_recommendation_callbacks_clear_results(self):
        ui = UI()
        code = APP.split('# ---------------- USER INPUT ----------------')[1].split('# ---------------- RECOMMENDATION BUTTON ----------------')[0]
        exec(code, {'st': ui, 'movie_list': ['Toy Story (1995)']})
        for label in ('Choose a movie you like:', 'Enter User ID:'):
            ui.session_state.recommendations = 'old results'
            ui.session_state.recommendation_error = True
            ui.inputs[label]['on_change']()
            self.assertIsNone(ui.session_state.recommendations)
            self.assertFalse(ui.session_state.recommendation_error)

    def test_comparison_survives_rerun_and_preserves_compared_pair(self):
        ui = UI()
        movies = pd.DataFrame({'title': ['One', 'Two', 'Three'], 'year': [1995]*3,
                               'genres': ['Comedy']*3, 'average_rating': [4.0]*3,
                               'rating_count': [10]*3})
        code = APP.split('# ---------------- MOVIE COMPARISON ----------------')[1].split('# ---------------- MY WATCHLIST ----------------')[0]
        env = {'st': ui, 'movies': movies, 'movie_list': movies.title.tolist(), 'pd': pd,
               'get_movie_details': lambda t: None, 'get_movie_poster': lambda t: None,
               'poster_urls': {}}
        ui.clicked = {'⚖️ Compare Movies'}
        exec(code, env)
        self.assertEqual(ui.session_state.comparison_movies, ('One', 'Two'))
        ui.clicked = set()
        ui.messages.clear()
        env['movie_list'] = ['Three', 'Two', 'One']
        exec(code, env)
        titles = [args[0] for name, args in ui.messages if name == 'subheader']
        self.assertEqual(titles, ['One', 'Two'])

    def test_same_movie_comparison_warns(self):
        ui = UI()
        ui.clicked = {'⚖️ Compare Movies'}
        code = APP.split('# ---------------- MOVIE COMPARISON ----------------')[1].split('# ---------------- MY WATCHLIST ----------------')[0]
        exec(code, {'st': ui, 'movie_list': ['One']})
        self.assertIn(('warning', ('Please select two different movies!',)), ui.messages)

    def test_hybrid_excludes_rated_and_seed_with_fewer_than_five_candidates(self):
        # Includes a rated movie with a zero centred rating: it must remain excluded.
        movies = pd.DataFrame({'movie_id': [10, 20, 30, 40], 'title': ['Seed', 'Rated at mean', 'New A', 'New B']})
        class Mask:
            def __getitem__(self, index):
                return SimpleNamespace(toarray=lambda: np.array([[False, True, False, False]]))
        env = functions(HYBRID, {'normalize', 'recommend_hybrid'}, {'np': np, 'pd': pd})
        env['load_model'] = lambda: (movies, np.eye(4), np.array([[5., 10., 3., 2.]]), {1: 0})
        env['load_rated_movie_ids'] = lambda: {1: {20}}
        result = env['recommend_hybrid']('Seed', 1)
        self.assertEqual(set(result.Movie), {'New A', 'New B'})
        self.assertTrue(np.isfinite(result['Hybrid Score']).all())
        self.assertIsNone(env['recommend_hybrid']('missing', 1))
        self.assertIsNone(env['recommend_hybrid']('Seed', 999))

    def test_hybrid_handles_no_eligible_candidates(self):
        movies = pd.DataFrame({'movie_id': [10], 'title': ['Seed']})
        class Mask:
            def __getitem__(self, index):
                return SimpleNamespace(toarray=lambda: np.array([[True]]))
        env = functions(HYBRID, {'normalize', 'recommend_hybrid'}, {'np': np, 'pd': pd})
        env['load_model'] = lambda: (movies, np.ones((1, 1)), np.ones((1, 1)), {1: 0})
        env['load_rated_movie_ids'] = lambda: {1: {10}}
        result = env['recommend_hybrid']('Seed', 1)
        self.assertTrue(result.empty)
        self.assertEqual(list(result.columns), ['Movie', 'Hybrid Score'])


if __name__ == '__main__':
    unittest.main()
