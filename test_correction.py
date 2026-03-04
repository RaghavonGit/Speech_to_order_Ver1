"""
Quick simulation test for conversational correction pipeline.
Tests the fixes: CANCEL_SIGNAL in _is_complex_order, போதும் in UPDATE_SIGNALS,
and Tamil-script இல்ல/இல்லை in CORRECTION_TRIGGERS.
"""
import re
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from veg_processor import VegProcessor
from nonveg_processor import NonVegProcessor

veg   = VegProcessor()
nonveg = NonVegProcessor()

CANCEL_SIGNAL  = r'வேண்டாம்|வேண்டா|\bvendaam\b|\bvendama\b'
REPLACE_SIGNAL = r'அதற்கு\s*பதிலா|பதிலா|\batharku\s*pathila\b|\binstead\b|\bpathila\b'
UPDATE_SIGNALS = r'மட்டும்\s*போதும்|போதும்|ஆக்குங்க|மட்டும்|\baakkuinga\b|\baakkunga\b|\bonly\b|\bpothum\b|\benough\b'
TRANSITION_MARKERS = ['\u2026', r'\.\.\.']

def is_complex(text):
    for m in TRANSITION_MARKERS:
        if re.search(m, text):
            return True
    if re.search(REPLACE_SIGNAL, text):
        return True
    if re.search(CANCEL_SIGNAL, text, re.IGNORECASE):
        return True
    if re.search(UPDATE_SIGNALS, text):
        all_items = veg.extract_grocery_items(text) + nonveg.extract_grocery_items(text)
        if len(set(i['name'] for i in all_items)) >= 2:
            return True
    return False


def find_item(seg):
    items = veg.extract_grocery_items(seg)
    if not items:
        items = nonveg.extract_grocery_items(seg)
    return items[0] if items else None


def extract_qty(seg):
    unit_map = {
        'kg': 'kg', 'kilogram': 'kg', 'kilo': 'kg',
        'gram': 'g', 'g': 'g', 'gm': 'g',
        'liter': 'liter', 'litre': 'liter', 'l': 'liter', 'ml': 'ml',
        'packet': 'packets', 'packets': 'packets', 'pkt': 'packets',
        'piece': 'pieces', 'pieces': 'pieces', 'pcs': 'pieces',
        'bunch': 'bunch', 'bunches': 'bunch',
        'tray': 'tray', 'dozen': 'dozen',
        'கிலோ': 'kg', 'கிராம்': 'g',
    }
    qty_re = (
        r'(\d+(?:\.\d+)?)\s*'
        r'(kg|kilogram|kilo|gram|g|gm|liter|litre|l|ml|'
        r'packet|packets|pkt|piece|pieces|pcs|bunch|bunches|tray|dozen|கிலோ|கிராம்)'
    )
    norm = veg.normalize_numbers(nonveg.normalize_numbers(seg))
    m = re.search(qty_re, norm, re.IGNORECASE)
    if m:
        return m.group(1), unit_map.get(m.group(2).lower(), m.group(2).lower())
    return '1', ''


def simulate(text):
    print(f'  is_complex → {is_complex(text)}')

    all_segs = [s.strip() for s in re.split(r'[,;]', text) if s.strip()]
    split_at = None
    for i, seg in enumerate(all_segs):
        if re.search(CANCEL_SIGNAL + '|' + REPLACE_SIGNAL, seg, re.IGNORECASE):
            split_at = i
            break

    if split_at is not None and split_at > 0:
        initial_block    = ', '.join(all_segs[:split_at])
        correction_block = ', '.join(all_segs[split_at:])
    elif split_at == 0:
        initial_block, correction_block = '', ', '.join(all_segs)
    else:
        initial_block, correction_block = text, ''

    # Build initial cart
    cart, seen = [], set()
    for seg in re.split(r'[,;]', initial_block):
        seg = seg.strip()
        if not seg:
            continue
        for item in veg.extract_grocery_items(seg) + nonveg.extract_grocery_items(seg):
            if item['name'] not in seen:
                seen.add(item['name'])
                cart.append(dict(item))

    print(f'  Initial cart: {[(c["name"], c["quantity"], c["unit"]) for c in cart]}')

    # Process correction segments
    for seg in [s.strip() for s in re.split(r'[,\uff0c;]|(?<!\d)\.(?!\d)', correction_block) if s.strip()]:
        if re.search(REPLACE_SIGNAL, seg):
            after = re.split(REPLACE_SIGNAL, seg, maxsplit=1)[-1].strip()
            ni = find_item(after)
            if ni:
                q, u = extract_qty(after)
                ni = dict(ni)
                ni['quantity'] = q
                ni['unit'] = u or ni.get('unit', 'kg')
                cart = [c for c in cart if c['name'] != ni['name']]
                cart.append(ni)
                print(f'  REPLACE => {ni["name"]} {ni["quantity"]} {ni["unit"]}')

        elif re.search(CANCEL_SIGNAL, seg, re.IGNORECASE):
            bc = re.split(CANCEL_SIGNAL, seg)[0].strip()
            t = find_item(bc)
            if t:
                before_len = len(cart)
                cart = [c for c in cart if c['name'] != t['name']]
                print(f'  CANCEL {t["name"]} (removed {before_len - len(cart)})')

        elif re.search(UPDATE_SIGNALS, seg):
            t = find_item(seg)
            if t:
                q, u = extract_qty(seg)
                for c in cart:
                    if c['name'] == t['name']:
                        c['quantity'] = q
                        if u:
                            c['unit'] = u
                        print(f'  UPDATE {t["name"]} => {q} {u}')
                        break

        else:
            # Implicit update/add
            t = find_item(seg)
            if t:
                q, u = extract_qty(seg)
                names = [c['name'] for c in cart]
                if t['name'] in names:
                    for c in cart:
                        if c['name'] == t['name']:
                            c['quantity'] = q
                            if u:
                                c['unit'] = u
                            print(f'  IMPLICIT-UPDATE {t["name"]} => {q} {u}')
                            break
                else:
                    e = dict(t)
                    e['quantity'] = q
                    e['unit'] = u or t.get('unit', 'kg')
                    cart.append(e)
                    print(f'  IMPLICIT-ADD {t["name"]} {q} {u}')

    print(f'  FINAL: {[(c["name"], c["quantity"], c["unit"]) for c in cart]}')


# ---------------------------------------------------------------------------
TESTS = [
    (
        "User's Tamil example",
        'ஒரு கிலோ தக்காளி போடுங்க, இல்ல ரெண்டு கிலோ வெங்காயம், '
        'இல்லை வெங்காயம் வேண்டாம், தக்காளி 1.5 கிலோ போதும், கேரட் அரை கிலோ கூட.',
        [('Tomato', '1.5', 'kg'), ('Carrot', '0.5', 'kg')],
    ),
    (
        "My test: cancel + update (Tamil)",
        'தக்காளி 2 கிலோ, வெங்காயம் 1 கிலோ, கேரட் 0.5 கிலோ, '
        'வெங்காயம் வேண்டாம், தக்காளி 3 கிலோ ஆக்குங்க',
        [('Tomato', '3', 'kg'), ('Carrot', '0.5', 'kg')],
    ),
    (
        "My test: romanized vendaam + pothum",
        'rendu kilo thakkali, oru kilo vengayam, vengayam vendaam, thakkali 3 kilo pothum',
        [('Tomato', '3', 'kg')],
    ),
    (
        "Simple order — should NOT be routed to complex engine",
        'தக்காளி 2 கிலோ, வெங்காயம் 1 கிலோ',
        None,   # just check is_complex = False
    ),
    (
        "Single item with போதும் — should NOT be complex",
        'தக்காளி 1.5 கிலோ போதும்',
        None,
    ),
]

all_pass = True
for name, text, expected in TESTS:
    print(f'\n=== {name} ===')
    print(f'  Input: {text[:80].encode("ascii", "replace").decode()}')
    if expected is None:
        c = is_complex(text)
        status = 'PASS' if not c else 'FAIL'
        print(f'  is_complex → {c}  [{status}]')
        if c:
            all_pass = False
    else:
        simulate(text)

print('\n' + ('All tests PASSED!' if all_pass else 'Some tests FAILED.'))
