#!/usr/bin/env python3
"""Build MS-C (scientific self-consistency errors) and MS-D (the corrected control).

T6 asks a different question from T1: not "does this manuscript follow the style rules"
but "are its numbers and claims consistent with each other". No amount of string
matching answers that, so it should discriminate between models in a way the format
checks did not.

Three of the ten seeded errors (S01, S02, S03) were already present in MS-B by accident.
They are kept rather than replaced: an inconsistency that arose from writing a plausible
manuscript is more representative than one designed to be found.

Both files are derived from MS-B, so MS-C carries no formatting violations -- a model
that reports style problems here is off-task, which is itself measured.

Idempotent: MS-C and MS-D are always rebuilt from MS-B.
"""
import pathlib, sys, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
base = (ROOT / 'data/manuscripts/MS-B.md').read_text()


def apply(text, label, pairs):
    for old, new in pairs:
        if old not in text:
            sys.exit(f'{label}: pattern not found: {old[:80]!r}')
        if text.count(old) != 1:
            sys.exit(f'{label}: pattern not unique ({text.count(old)}x): {old[:80]!r}')
        text = text.replace(old, new)
    return text


# --------------------------------------------------------------- MS-C
# S01, S02, S03 are inherited from MS-B unchanged. S04-S10 are introduced here.
c = base
c = apply(c, 'header', [
    ('[Manuscript ID: BPPB-2026-0417]', '[Manuscript ID: BPPB-2026-0512]')])

# S04 abstract contradicts Results and Table 2 (2.31 CCW)
c = apply(c, 'S04', [
    ('computed from the network covariance matrix gives an effective length constant of 2.3\nsubunits counter-clockwise against 0.7 subunits clockwise.',
     'computed from the network covariance matrix gives an effective length constant of 3.2\nsubunits counter-clockwise against 0.7 subunits clockwise.')])

# S05 Table 2 ratio for s = 3.2 is wrong (2.42 / 0.69 = 3.51)
c = apply(c, 'S05', [
    ('  3.2     2.42                  0.69                 3.51',
     '  3.2     2.42                  0.69                 4.51')])

# S06 "effectively isotropic" asserted while a 2.6x anisotropy remains
c = apply(c, 'S06', [
    ('length constant to 0.9 subunits while leaving the clockwise value unchanged, so that\nthe channel becomes effectively isotropic.',
     'length constant to 1.8 subunits while leaving the clockwise value unchanged, so that\nthe channel becomes effectively isotropic.')])

# S07 Results contradict the Methods run count (thirty)
c = apply(c, 'S07', [
    ('The mean rotation rate saturates above a driving\nfrequency of about 400 s^-1, and the saturation value is within a factor of two of the\nmeasured maximum rate.',
     'The mean rotation rate, averaged over five independent runs, saturates above a driving\nfrequency of about 400 s^-1, and the saturation value is within a factor of two of the\nmeasured maximum rate.')])

# S08 cutoff given in nm in the Methods, in angstroms everywhere else
c = apply(c, 'S08', [
    ('Beads separated by less than a cutoff distance of 12 A were connected by harmonic',
     'Beads separated by less than a cutoff distance of 12 nm were connected by harmonic')])

# S09 robustness range overstated (2.0-3.6 is a factor of 1.8)
c = apply(c, 'S09', [
    ('We have shown that the qualitative conclusions are robust across a\nfactor of nearly two in s,',
     'We have shown that the qualitative conclusions are robust across a\nfactor of nearly ten in s,')])

# S10 timestep is an all-atom value, incompatible with coarse-grained overdamped dynamics
#     and with the millisecond processes the paper claims to resolve. (Inherited from
#     MS-B as written; restated here so the control can differ.)
assert 'time step of 20 fs' in c

(ROOT / 'data/manuscripts/MS-C.md').write_text(c)
print('MS-C written:', len(c.split()), 'words')

# --------------------------------------------------------------- MS-D (control)
d = c
d = apply(d, 'D-header', [
    ('[Manuscript ID: BPPB-2026-0512]', '[Manuscript ID: BPPB-2026-0513]')])
# revert S04..S09
d = apply(d, 'D-S04', [('effective length constant of 3.2\nsubunits counter-clockwise',
                        'effective length constant of 2.3\nsubunits counter-clockwise')])
d = apply(d, 'D-S05', [('  3.2     2.42                  0.69                 4.51',
                        '  3.2     2.42                  0.69                 3.51')])
d = apply(d, 'D-S06', [('length constant to 1.8 subunits while leaving the clockwise value unchanged, so that\nthe channel becomes effectively isotropic.',
                        'length constant to 0.9 subunits while leaving the clockwise value unchanged, so that\nthe channel becomes nearly isotropic.')])
d = apply(d, 'D-S07', [('The mean rotation rate, averaged over five independent runs, saturates above a driving',
                        'The mean rotation rate saturates above a driving')])
d = apply(d, 'D-S08', [('cutoff distance of 12 nm were connected', 'cutoff distance of 12 A were connected')])
d = apply(d, 'D-S09', [('robust across a\nfactor of nearly ten in s,', 'robust across a\nfactor of nearly two in s,')])
# fix S10: overdamped coarse-grained dynamics use a picosecond-scale step
d = apply(d, 'D-S10', [('integrated with a time step of 20 fs and a uniform',
                        'integrated with a time step of 50 ps and a uniform')])
# fix S03: a 400 s^-1 saturation needs runs long enough to contain several periods
d = apply(d, 'D-S03', [('run covered 200 ns and thirty independent runs were performed for each condition.',
                        'run covered 20 ms and thirty independent runs were performed for each condition.')])
# fix S02: one bead per alpha-carbon means bead count = chain length, and the C-terminal
#          helix at residues 471-489 puts the chain at 489 residues
# fix S01: truncating one subunit removes 19 beads, not 114
d = apply(d, 'D-S01/S02-text', [
    ('contained 18,204 beads and 412,806 springs (Table 1).',
     'contained 2,934 beads and 66,526 springs (Table 1).')])
d = apply(d, 'D-S01/S02-table', [(
    """  Hexamer, apo           18204     412806      12
  Hexamer, 2 adjacent    18204     412806      12
  Hexamer, truncated     18090     409911      12
  Monomer                 3034      66471      12""",
    """  Hexamer, apo            2934      66526      12
  Hexamer, 2 adjacent     2934      66526      12
  Hexamer, truncated      2915      66051      12
  Monomer                  489      10712      12""")])

(ROOT / 'data/manuscripts/MS-D.md').write_text(d)
print('MS-D written:', len(d.split()), 'words')
