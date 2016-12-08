import os
import string
import sw as app
                
if app.app_api_version()<'1.0.158':
    app.msg_box(app.MSG_ERROR, 'Hilite plugin needs newer app version')

#----------------------Settings---------------------#
MIN_LEN  = 2 # For word or selected text
MAX_SIZE = 400*1000 # Max allowed chars count

SEL_ALLOW             = True  # Hilite all occurrences of selected text
SEL_ALLOW_WHITE_SPACE = False # Hilite spaces located in begin or end of selection
SEL_CASE_SENSITIVE    = False
SEL_WORDS_ONLY        = False # Hilite char only if it's in CHARS
SEL_WHOLE_WORDS       = False # Whole word only. Used only if bool(SEL_WORDS_ONLY)

CARET_ALLOW          = True # Hilite all occurrences of word under caret
CARET_CASE_SENSITIVE = True
CARET_WHOLE_WORDS    = True # Whole word only
#-----------------------------------------------#

CHARS = string.ascii_letters + string.digits + '_'
fn_ini = os.path.join(app.app_ini_dir(), 'syn_hilite.ini')
MARKTAG = 102 #uniq value for all search-marks plugins


def do_load_ops():
  global MIN_LEN
  global MAX_SIZE
  global SEL_ALLOW
  global SEL_ALLOW_WHITE_SPACE
  global SEL_CASE_SENSITIVE
  global SEL_WORDS_ONLY
  global SEL_WHOLE_WORDS
  global CARET_ALLOW
  global CARET_CASE_SENSITIVE
  global CARET_WHOLE_WORDS

  MIN_LEN               = int(app.ini_read(fn_ini, 'op', 'min_len', str(MIN_LEN)))
  MAX_SIZE              = int(app.ini_read(fn_ini, 'op', 'max_size', str(MAX_SIZE)))

  SEL_ALLOW             = app.ini_read(fn_ini, 'op', 'sel_allow', '1')=='1'
  SEL_ALLOW_WHITE_SPACE = app.ini_read(fn_ini, 'op', 'sel_allow_white_space', '0')=='1'
  SEL_CASE_SENSITIVE    = app.ini_read(fn_ini, 'op', 'sel_case_sensitive', '0')=='1'
  SEL_WORDS_ONLY        = app.ini_read(fn_ini, 'op', 'sel_words_only', '0')=='1'
  SEL_WHOLE_WORDS       = app.ini_read(fn_ini, 'op', 'sel_whole_words', '0')=='1'

  CARET_ALLOW           = app.ini_read(fn_ini, 'op', 'caret_allow', '1')=='1'
  CARET_CASE_SENSITIVE  = app.ini_read(fn_ini, 'op', 'caret_case_sensitive', '1')=='1'
  CARET_WHOLE_WORDS     = app.ini_read(fn_ini, 'op', 'caret_whole_words', '1')=='1'


def bool_str(b):
  return '1' if b else '0'


def do_save_ops():
  app.ini_write(fn_ini, 'op', 'min_len', str(MIN_LEN))
  app.ini_write(fn_ini, 'op', 'max_size', str(MAX_SIZE))

  app.ini_write(fn_ini, 'op', 'sel_allow', bool_str(SEL_ALLOW))
  app.ini_write(fn_ini, 'op', 'sel_allow_white_space', bool_str(SEL_ALLOW_WHITE_SPACE))
  app.ini_write(fn_ini, 'op', 'sel_case_sensitive', bool_str(SEL_CASE_SENSITIVE))
  app.ini_write(fn_ini, 'op', 'sel_words_only', bool_str(SEL_WORDS_ONLY))
  app.ini_write(fn_ini, 'op', 'sel_whole_words', bool_str(SEL_WHOLE_WORDS))

  app.ini_write(fn_ini, 'op', 'caret_allow', bool_str(CARET_ALLOW))
  app.ini_write(fn_ini, 'op', 'caret_case_sensitive', bool_str(CARET_CASE_SENSITIVE))
  app.ini_write(fn_ini, 'op', 'caret_whole_words', bool_str(CARET_WHOLE_WORDS))


class Command:
  def __init__(self):
    do_load_ops()

  def config(self):
    do_save_ops()
    if os.path.isfile(fn_ini):
      app.file_open(fn_ini)
    else:
      app.msg_status('Config file not exists')

  def on_caret_move(self, ed_self):
    if ed_self.get_carets(): return #donot allow mul-carets
    if ed_self.get_text_len() > MAX_SIZE: return

    ed_self.marks(app.MARKS_DELETE_BY_TAG, 0, 0, MARKTAG)

    current_text = _get_current_text(ed_self)
    if not current_text: return
    text, caret_pos, is_selection = current_text

    if not SEL_ALLOW_WHITE_SPACE: text = text.strip()
    if not text: return

    if is_selection:
      case_sensitive = SEL_CASE_SENSITIVE
      words_only     = SEL_WORDS_ONLY
      whole_words    = SEL_WHOLE_WORDS if SEL_WORDS_ONLY else False
    else:
      case_sensitive = CARET_CASE_SENSITIVE
      words_only     = True
      whole_words    = CARET_WHOLE_WORDS

    if len(text) < MIN_LEN: return

    x0, y0, x1, y1 = caret_pos
    if x0 > x1: x0, x1 = x1, x0

    items = find_all_occurrences(ed_self, text, case_sensitive, whole_words, words_only)

    if not items: return
    if len(items) == 1 and items[0] == (x0, y1): return

    for item in items:
      if item == (x0, y0): continue

      npos = ed_self.xy_pos(item[0], item[1])
      ed_self.marks(app.MARKS_ADD, npos, len(text), MARKTAG)
    else:
      if CARET_ALLOW and not is_selection:
        npos = ed_self.xy_pos(x0, y0)
        ed_self.marks(app.MARKS_ADD, npos, len(text), MARKTAG)

    app.msg_status('Matches hilited: {}'.format(len(items)))

def is_word(s):
  for ch in s:
    if not ch in CHARS: return False
  return True

def find_all_occurrences(ed, text, case_sensitive, whole_words, words_only):
  if words_only and not is_word(text): return

  if not case_sensitive: text = text.lower()

  res = []
  for y in range(ed.get_line_count()):
    line = ed.get_text_line(y)
    if not line: continue

    if not case_sensitive: line = line.lower()

    x = 0
    text_len = len(text)
    while True:
      x = line.find(text, x)
      if x < 0: break

      if whole_words:
        if x > 0 and is_word(line[x - 1]):
          x += text_len + 1
          continue

        next_char = x + text_len
        if next_char < len(line) and is_word(line[next_char]):
          x += 2
          continue

      res.append((x, y))

      x += text_len

  return res

def get_word_under_caret(ed):
  '''Возвращает кортеж (слово_под_кареткой, (x1, y1, x2, y2)) (не учитывая, есть выделение или нет).'''

  x1, y1 = ed.get_caret_xy()
  npos, nlen = ed.get_sel()
  x2, y2 = x1+nlen, y1 #can do since no mulline

  l_char = r_char = ''
  current_line = ed.get_text_line(y1)

  if current_line:
    x = x1
    if x > 0:                 l_char = current_line[x - 1]
    if x < len(current_line): r_char = current_line[x]

    l_char, r_char = is_word(l_char), is_word(r_char)

    if not (l_char or r_char): return

    if l_char:
      for x1 in range(x - 1, -1, -1):
        if is_word(current_line[x1]): continue
        else: break
      else: x1 = -1
      x1 += 1

    if r_char:
      for x2 in range(x + 1, len(current_line)):
        if is_word(current_line[x2]): continue
        else: break
      else: x2 = len(current_line)
    else: x2 = x

    word_under_caret = current_line[x1 : x2]
  else: return

  return word_under_caret, (x1, y1, x2, y2)

def _get_current_text(ed):
  x1, y1 = ed.get_caret_xy()
  npos, nlen = ed.get_sel()
  is_sel = nlen>0
  text = ''

  if is_sel:
    if not SEL_ALLOW: return
    text = ed.get_text_sel()
    #dont allow mulline
    if '\n' in text: return
    if '\r' in text: return
    caret = (x1, y1, x1+nlen, y1)
  else:
    if not CARET_ALLOW: return
    if y1>=ed.get_line_count(): return
    if len(ed.get_text_line(y1)) < x1: return
    temp = get_word_under_caret(ed)
    if not temp: return
    text, caret = temp

  return text, caret, is_sel
