#!/usr/bin/env python3
"""Verify MS-C's seeded errors are real and MS-D is fully self-consistent.

Run this before trusting any T6 number. Every claim in the ground truth is checked here
arithmetically, because the earlier rounds of this project were repeatedly derailed by
ground truth that was itself wrong (dashes, brittle anchors, a 'compliant' control that
cited figures out of order).
"""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def flat(t):
    """Join wrapped lines so patterns spanning a line break still match."""
    return re.sub(r'\s+', ' ', t)


def table(t):
    return {'hexa': int(re.search(r'Hexamer, apo\s+(\d+)', t).group(1)),
            'trunc': int(re.search(r'Hexamer, truncated\s+(\d+)', t).group(1)),
            'mono': int(re.search(r'Monomer\s+(\d+)', t).group(1)),
            'sp_h': int(re.search(r'Hexamer, apo\s+\d+\s+(\d+)', t).group(1)),
            'sp_t': int(re.search(r'Hexamer, truncated\s+\d+\s+(\d+)', t).group(1)),
            'sp_m': int(re.search(r'Monomer\s+\d+\s+(\d+)', t).group(1))}


def runtime_s(t):
    m = re.search(r'run covered (\d+) (\w+)', t)
    return int(m.group(1)) * {'ns': 1e-9, 'us': 1e-6, 'ms': 1e-3, 's': 1}[m.group(2)], m.group(0)


def ratios(t):
    return [tuple(map(float, r)) for r in
            re.findall(r'^  (\d\.\d)\s+(\d\.\d+)\s+(\d\.\d+)\s+(\d\.\d+)$', t, re.M)]


def check(name, cond, msg, bad):
    print(f"  {'OK  ' if cond else 'FAIL'}  {name}: {msg}")
    if not cond:
        bad.append(f'{name}: {msg}')


def main():
    bad = []
    c = (ROOT / 'data/manuscripts/MS-C.md').read_text()
    d = (ROOT / 'data/manuscripts/MS-D.md').read_text()
    fc, fd = flat(c), flat(d)

    print('=== MS-C: each seeded error present and genuinely wrong ===')
    tc = table(c)
    check('S01', tc['hexa'] - tc['trunc'] == 114 and 114 == 6 * 19,
          f"truncation removes {tc['hexa']-tc['trunc']} beads for 19 residues of one subunit (= 6x)", bad)
    check('S02', tc['mono'] == 3034,
          f"monomer {tc['mono']} beads = {tc['mono']} residues, but the C-terminal helix is residues 471-489", bad)
    rs, txt = runtime_s(c)
    T = 1 / int(re.search(r'frequency of about (\d+) s\^-1', c).group(1))
    check('S03', rs < T / 100, f'{txt} = {rs:.3g} s covers {rs/T:.2e} of a {T*1e3:.1f} ms period', bad)
    ab = re.search(r'length constant of (\d\.\d) subunits counter-clockwise', fc).group(1)
    rr = re.search(r'effective length constant of (\d\.\d) subunits in the counter-clockwise', fc).group(1)
    check('S04', ab != rr, f'abstract {ab} vs Results {rr}', bad)
    r32 = [r for r in ratios(c) if r[0] == 3.2][0]
    check('S05', abs(r32[1] / r32[2] - r32[3]) > 0.5,
          f'Table 2 s=3.2: {r32[1]}/{r32[2]} = {r32[1]/r32[2]:.3f} listed as {r32[3]}', bad)
    tr = re.search(r'length constant to (\d\.\d) subunits .*? channel becomes (\w+) isotropic', fc)
    cwv = [r for r in ratios(c) if r[0] == 2.8][0][2]
    check('S06', float(tr.group(1)) / cwv > 2,
          f'"{tr.group(2)} isotropic" with {tr.group(1)}/{cwv} = {float(tr.group(1))/cwv:.1f}x remaining', bad)
    check('S07', 'averaged over five independent runs' in fc and 'thirty independent runs' in fc,
          'Methods say thirty runs, Results say five', bad)
    check('S08', 'cutoff distance of 12 nm' in fc and 'Cutoff (A)' in c and 'between 10 and 14 A' in fc,
          'cutoff given as 12 nm in Methods, angstroms elsewhere', bad)
    check('S09', 'factor of nearly ten in s' in fc, 'claims factor of ten; tested 2.0-3.6 = 1.8', bad)
    check('S10', 'time step of 20 fs' in fc, '20 fs step for coarse-grained overdamped dynamics', bad)

    print('\n=== MS-C distractors: correct claims that look suspicious ===')
    for n, cond, msg in [
        ('SD1', 'six zero-frequency modes were projected out' in fc,
         'six zero-frequency modes projected out (correct for a 3D network)'),
        ('SD2', tc['sp_h'] > 6 * tc['sp_m'],
         f"hexamer springs {tc['sp_h']} > 6 x monomer {6*tc['sp_m']} (excess is interfacial)"),
        ('SD3', tc['hexa'] == 6 * tc['mono'], 'hexamer beads exactly 6 x monomer'),
        ('SD4', '2.8 +/- 0.4' in fc, 'calibration 2.8 +/- 0.4 with sensitivity explored over a wider range'),
        ('SD5', 'within a factor of two' in fc, 'agreement "within a factor of two" stated honestly')]:
        check(n, cond, msg, bad)

    print('\n=== MS-D: control must be fully self-consistent ===')
    td = table(d)
    check('D-beads', td['hexa'] == 6 * td['mono'], f"{td['hexa']} == 6 x {td['mono']}", bad)
    check('D-trunc', td['hexa'] - td['trunc'] == 19, f"removes {td['hexa']-td['trunc']} beads for 19 residues", bad)
    check('D-springs', td['sp_h'] >= 6 * td['sp_m'], f"{td['sp_h']} >= {6*td['sp_m']}", bad)
    check('D-trspr', td['sp_t'] < td['sp_h'], f"{td['sp_t']} < {td['sp_h']}", bad)
    m = re.search(r'contained ([\d,]+) beads and ([\d,]+) springs', fd)
    check('D-text', int(m.group(1).replace(',', '')) == td['hexa'] and
          int(m.group(2).replace(',', '')) == td['sp_h'], f'Methods text matches Table 1 ({m.group(1)}, {m.group(2)})', bad)
    check('D-chain', td['mono'] == 489, f"monomer {td['mono']} beads consistent with residues 471-489 being the C-terminus", bad)
    for s, ccw, cw, r in ratios(d):
        check(f'D-ratio-{s}', abs(ccw / cw - r) < 0.01, f'{ccw}/{cw} = {ccw/cw:.3f} vs {r}', bad)
    abd = re.search(r'length constant of (\d\.\d) subunits counter-clockwise', fd).group(1)
    rrd = re.search(r'effective length constant of (\d\.\d) subunits in the counter-clockwise', fd).group(1)
    check('D-abstract', abd == rrd, f'abstract {abd} == Results {rrd}', bad)
    rsd, txtd = runtime_s(d)
    check('D-runtime', rsd > 3 * T, f'{txtd} covers {rsd/T:.1f} periods', bad)
    check('D-robust', 'factor of nearly two in s' in fd, 'robustness claim matches the 1.8x tested range', bad)
    check('D-step', re.search(r'time step of (\d+) (\w+)', fd).group(2) == 'ps', 'time step on the ps scale', bad)
    check('D-runs', 'averaged over five independent runs' not in fd and 'thirty independent runs' in fd,
          'run count stated once', bad)
    check('D-cutoff', '12 A were connected' in fd and '12 nm' not in fd, 'cutoff in angstroms only', bad)
    trd = re.search(r'channel becomes (\w+) isotropic', fd).group(1)
    cwd = [r for r in ratios(d) if r[0] == 2.8][0][2]
    trv = float(re.search(r'length constant to (\d\.\d) subunits', fd).group(1))
    check('D-isotropic', trv / cwd < 1.5, f'"{trd} isotropic" with {trv}/{cwd} = {trv/cwd:.2f}x remaining', bad)

    print(f'\n{len(bad)} problem(s)')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
