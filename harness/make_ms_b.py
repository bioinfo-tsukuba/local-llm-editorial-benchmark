#!/usr/bin/env python3
"""Generate MS-B (fully BPPB-compliant control) from MS-A by fixing each seeded violation.

Run order: this script first, then fix_ms_b_figures.py. This script's final post-pass
mutates MS-A itself (it moves the tables/figures block to the end of BOTH manuscripts),
so it is deliberately single-use per MS-A revision and will abort rather than corrupt
an already-processed MS-A.

Every substitution is tagged with the violation ID it repairs so the two manuscripts
stay in one-to-one correspondence. MS-B exists to measure the false-positive rate:
a compliant manuscript should yield zero findings.
"""
import re, sys, pathlib

src = pathlib.Path('data/manuscripts/MS-A.md').read_text()
t = src

def sub(vid, old, new, count=1):
    global t
    n = t.count(old)
    if n < 1:
        sys.exit(f'{vid}: pattern not found: {old[:70]!r}')
    t = t.replace(old, new, count)

# --- V07 running title 78 -> <=50 chars -------------------------------------
sub('V07',
    'Running title: Coarse-grained elastic network analysis of allosteric coupling in ring ATPases',
    'Running title: Allosteric coupling in ring ATPases')

# --- V01 remove prohibited positive word from title ------------------------
sub('V01',
    'Novel coarse-grained model of allosteric communication in a ring-shaped ATPase\n\nKenji',
    'A coarse-grained model of allosteric communication in a ring-shaped ATPase\n\nKenji')

# --- V08/V09 complete postal address + ORCID iD ---------------------------
sub('V08+V09',
    '*Corresponding author: Hideo Kuramoto, Department of Molecular Biophysics, Kitagawa Institute of Technology, Kyoto\nE-mail: kuramoto@kit-mb.example.ac.jp',
    '*Corresponding author: Hideo Kuramoto, Department of Molecular Biophysics,\n'
    'Kitagawa Institute of Technology, 3-14-2 Nishikyogoku, Ukyo-ku, Kyoto 615-0882, Japan\n'
    'ORCID iD: https://orcid.org/0000-0002-1825-0097\n'
    'E-mail: kuramoto@kit-mb.example.ac.jp')

# --- V02/V03/V04 abstract: 330 -> <250 words, no citation, no "first time" --
old_abs_start = t.index('Abstract\n\nRing-shaped ATPases')
old_abs_end = t.index('\nKeywords:')
new_abs = """Abstract

Ring-shaped ATPases convert the chemical free energy of nucleotide hydrolysis into
directed mechanical rotation, and the mechanism by which the six catalytic subunits
communicate their nucleotide occupancy around the ring remains only partially
understood. Here we construct a coarse-grained elastic network representation of a
hexameric ring ATPase and analyze how a local perturbation at one nucleotide binding
pocket propagates to the neighbouring subunits. The model retains one bead per residue
and augments the standard anisotropic network potential with a nucleotide-dependent
term that stiffens the P-loop region upon ligand binding, which allows individual
subunits to be switched between apo-like and bound-like states without
re-parameterizing the entire network. Normal mode analysis shows that the three lowest
non-trivial modes reorganize substantially when two adjacent subunits are occupied,
whereas occupancy of two subunits on opposite sides of the ring leaves the
low-frequency spectrum nearly unchanged. A perturbation-response susceptibility
computed from the network covariance matrix gives an effective length constant of 2.3
subunits counter-clockwise against 0.7 subunits clockwise. Brownian dynamics simulations of the
same network under a periodic chemical driving protocol reproduce the sequential firing
order observed in single-molecule rotation assays. Truncating the C-terminal helix of a
single subunit abolishes the directionality of the susceptibility without measurably
changing the equilibrium fluctuation amplitude of the ring, which suggests that the
directional channel is carried by a small number of specific contacts rather than by
the global elastic architecture. These results provide a minimal physical picture of
intersubunit communication in ring ATPases.
"""
t = t[:old_abs_start] + new_abs + t[old_abs_end:]

# --- V05 seven keywords -> five -------------------------------------------
sub('V05',
    'Keywords: elastic network model, allostery, ring ATPase, normal mode analysis, coarse-grained simulation, molecular motor, Brownian dynamics',
    'Keywords: elastic network model, allostery, ring ATPase, normal mode analysis, Brownian dynamics')

# --- V06 significance 123 -> <100 words -----------------------------------
sig_start = t.index('Significance\n\nRing-shaped ATPases are among')
sig_end = t.index('\nIntroduction')
new_sig = """Significance

Understanding how the subunits of a ring-shaped ATPase coordinate their catalytic
cycles is a long-standing problem in biophysics. This study introduces a
coarse-grained elastic network model in which the nucleotide state of each subunit can
be switched independently, making it possible to map the directionality of allosteric
communication around the ring at low computational cost. The communication channel is
strongly asymmetric and is carried by a small number of contacts near the C-terminal
helix, a prediction that can be tested by truncation experiments.
"""
t = t[:sig_start] + new_sig + t[sig_end:]

# --- V31 parenthetical citation -> brackets -------------------------------
sub('V31', 'at the subunit interfaces\n(1, 2).', 'at the subunit interfaces\n[1,2].')

# --- V14 preprint statement out of Introduction ---------------------------
sub('V14',
    ' A preliminary version of this work was deposited\nin bioRxiv on 4 March 2026.',
    '')

# --- V32 PDB citation format ----------------------------------------------
sub('V32', 'are accessible (PDB 6qw9).',
    'are accessible [PDB ID: 6qw9] (https://doi.org/10.2210/pdb6qw9/pdb).')

# --- V39 animal ethics approval statement ---------------------------------
sub('V39',
    'Myosin used as a reference standard in the calibration measurements was purified from\nrabbit skeletal muscle by the standard procedure.',
    'Myosin used as a reference standard in the calibration measurements was purified from\n'
    'rabbit skeletal muscle by the standard procedure. All animal procedures were\n'
    'approved by the Institutional Animal Care and Use Committee of the Kitagawa\n'
    'Institute of Technology (approval no. 2025-041) and were carried out in accordance\n'
    'with its guidelines.')

# --- V21 figure citation order (Figure 1 before Figure 2) -----------------
sub('V21',
    """Figure 2 shows the frequency spectrum of the network for three occupancy patterns:
fully apo, two adjacent subunits bound, and two opposite subunits bound. The three
lowest non-trivial modes of the fully apo ring are the expected degenerate pair of
in-plane shear modes and a breathing mode. When two adjacent subunits are switched to
the bound state the degeneracy is lifted and the mode ordering changes, whereas the
opposite-subunit pattern leaves the spectrum essentially unchanged. Figure 1 shows the
corresponding mode displacement fields, in which the localization of the shear mode
onto the unoccupied side of the ring is clearly visible for the adjacent pattern.""",
    """Figure 1 shows the mode displacement fields of the three lowest non-trivial modes,
in which the localization of the shear mode onto the unoccupied side of the ring is
clearly visible for the adjacent pattern. The corresponding frequency spectra for the
three occupancy patterns are shown in Figure 2. The three lowest non-trivial modes of
the fully apo ring are the expected degenerate pair of in-plane shear modes and a
breathing mode. When two adjacent subunits are switched to the bound state the
degeneracy is lifted and the mode ordering changes, whereas the opposite-subunit
pattern leaves the spectrum essentially unchanged.""")

# --- V15/V16 cite Table 1, and cite it before Table 2 ---------------------
sub('V15+V16',
    'The full network for the hexamer\ncontained 18,204 beads and 412,806 springs.',
    'The full network for the hexamer\ncontained 18,204 beads and 412,806 springs (Table 1).')

# --- V20 cite Figure 3 ----------------------------------------------------
sub('V20',
    'A\nresidue-level decomposition of the susceptibility change identifies six contacts, all',
    'A\nresidue-level decomposition of the susceptibility change (Figure 3) identifies six\ncontacts, all')

# --- V10/V11/V12/V13 end-matter: Conclusion, order, Data availability -----
# Original: Author contributions -> Conflict of interest -> Tables ... -> References -> Acknowledgements
ac_start = t.index('Author contributions\n\nK.M. and H.K. designed')
ac_end = t.index('\nTables\n')
new_endmatter = """Conclusion

A coarse-grained elastic network model with an independently switchable nucleotide
state per subunit shows that allosteric communication around a hexameric ring ATPase
is strongly directional, with an effective length constant of 2.3 subunits in one
direction against 0.7 in the other. The directionality is carried by six interfacial
contacts involving the C-terminal helix, and it is abolished by truncating that helix
without disturbing the global elastic architecture of the ring.

Conflict of interest

K.M., A.T., R.N., S.J.W. and H.K. declare that they have no conflict of interest.

Author contributions

K.M. and H.K. designed the research and co-wrote the manuscript. K.M. and A.T.
constructed the elastic network model and performed the normal mode analysis. R.N.
implemented and ran the Brownian dynamics simulations. S.J.W. performed the
single-molecule rotation assays and analyzed the dwell time distributions. All authors
discussed the results and approved the final version of the manuscript.

Data availability

The evidence data generated and analyzed during the current study are available from
the corresponding author on reasonable request. The elastic network coordinate files
and susceptibility matrices have been deposited in J-STAGE Data
(https://doi.org/10.50931/data.biophysico.00000000).

A preliminary version of this work was deposited in bioRxiv (https://doi.org/10.1101/2026.03.04.000000) on 4 March 2026.

Acknowledgements

We thank the members of the Kitagawa Institute computing centre for technical support.
This work was supported by JSPS KAKENHI grant numbers 21K06789 and 23H01234.
"""
t = t[:ac_start] + new_endmatter + t[ac_end:]
# remove the now-duplicated trailing Acknowledgements after References
tail_ack = """
Acknowledgements

We thank the members of the Kitagawa Institute computing centre for technical support.
This work was supported by JSPS KAKENHI grant numbers 21K06789 and 23H01234.
"""
assert t.rstrip().endswith('23H01234.')
i = t.rindex(tail_ack)
t = t[:i].rstrip() + '\n'

# --- V17/V18/V19 tables: no vertical lines, title above, lettered footnotes
tbl_start = t.index('Tables\n\n  Table 1 |')
tbl_end = t.index('\nFigure legends')
new_tables = """Tables

  Table 1  Bead and spring counts for the networks used in this study.
  ------------------------------------------------------------------
  Network                Beads     Springs     Cutoff (A)
  ------------------------------------------------------------------
  Hexamer, apo           18204     412806      12
  Hexamer, 2 adjacent    18204     412806      12
  Hexamer, truncated     18090     409911      12
  Monomer                 3034      66471      12
  ------------------------------------------------------------------
  a. Cutoff applies to non-local springs only.
  b. Truncation removes residues 471-489 of subunit A.
  c. Counts exclude nucleotide beads.

  Table 2  Dependence of the fitted susceptibility length constants on the
  nucleotide stiffening factor s.
  ------------------------------------------------------------------
  s       CCW length constant   CW length constant   Ratio
  ------------------------------------------------------------------
  2.0     2.05                  0.74                 2.77
  2.4     2.19                  0.72                 3.04
  2.8     2.31                  0.70                 3.30
  3.2     2.42                  0.69                 3.51
  3.6     2.51                  0.68                 3.69
  ------------------------------------------------------------------
"""
t = t[:tbl_start] + new_tables + t[tbl_end:]

# --- V22/V23/V24 figure formats and resolution ---------------------------
sub('V22+V23+V24',
    """Figure file list
  Fig1_modes.bmp        150 dpi, colour
  Fig2_spectra.bmp      150 dpi, colour
  Fig3_heatmap.png      600 dpi, colour
  Fig4_susceptibility.png   600 dpi, greyscale
  Graphical_abstract.tiff   300 dpi, colour""",
    """Figure file list
  Fig1_modes.tiff       300 dpi, colour
  Fig2_spectra.tiff     300 dpi, colour
  Fig3_heatmap.png      600 dpi, colour
  Fig4_susceptibility.png   600 dpi, greyscale
  Graphical_abstract.png    300 dpi, colour""")

# --- V27/V28/V29/V30 supplementary names, formats, size ------------------
sub('V27+V28+V29+V30',
    """Supplementary materials
  Suppl_Fig_1.pdf   Convergence of the Brownian dynamics runs
  Suppl_Table_1.xlsx   Full susceptibility matrices
  Suppl_Movie_1.mov   Animation of the lowest shear mode (45 MB)
  図1_final version.tiff   High-resolution version of Figure 1""",
    """Supplementary materials
  Supplementary Figure S1 (SupplementaryFigureS1.pdf)   Convergence of the Brownian dynamics runs
  Supplementary Table S1 (SupplementaryTableS1.xlsx)   Full susceptibility matrices
  Supplementary Movie S1 (SupplementaryMovieS1.mpeg)   Animation of the lowest shear mode (18 MB)""")

# --- V25/V26 graphical abstract caption: <100 words, no title duplication -
ga_start = t.index('Graphical abstract caption\n')
ga_end = t.index('\nReferences')
new_ga = """Graphical abstract caption

The elastic network of a hexameric ring ATPase is drawn with one subunit switched to
the nucleotide-bound state, and the arrows show the perturbation-response
susceptibility transmitted to each neighbour. The colour scale indicates the
magnitude of the response, which decays over 2.3 subunits counter-clockwise but only
0.7 subunits clockwise. The inset marks the six interfacial contacts that carry this
asymmetry.
"""
t = t[:ga_start] + new_ga + t[ga_end:]

# --- V33 reference order [6] before [7] ----------------------------------
r6 = """[6] Togashi, Y., Mikhailov, A. S. Nonlinear relaxation dynamics in elastic networks
and design principles of molecular machines. Proc. Natl. Acad. Sci. U.S.A. 104,
8697-8702 (2007). https://doi.org/10.1073/pnas.0702950104
"""
r7 = """[7] Ikeguchi, M., Ueno, J., Sato, M., Kidera, A. Protein structural change upon ligand
binding: linear response theory. Phys. Rev. Lett. 94, 078102 (2005).
https://doi.org/10.1103/PhysRevLett.94.078102
"""
sub('V33', r7 + '\n' + r6, r6 + '\n' + r7)

# --- V34 "In preparation" reference -> published form --------------------
sub('V34',
    '[5] Nishimura, R., Morisawa, K. Directional coupling in driven elastic networks. In\npreparation.',
    '[5] Nishimura, R., Morisawa, K. Directional coupling in driven elastic networks.\n'
    'Biophys. Physicobiol. 22, 41-53 (2025). https://doi.org/10.2142/biophysico.bppb-v22.0041')

# --- V35 personal communication out of the reference list ---------------
sub('V35', '[8] Kuramoto, H. Personal communication, 2025.',
    '[8] Kuramoto, H., Morisawa, K. Elastic network analysis of chaperonin rings.\n'
    'Biophys. Physicobiol. 23, 8-19 (2026). https://doi.org/10.2142/biophysico.bppb-v23.0008')

# --- V36 nine authors -> six + et al. -----------------------------------
sub('V36',
    """[9] Adachi, K., Oiwa, K., Nishizaka, T., Furuike, S., Noji, H., Itoh, H., Yoshida, M.,
Kinosita, K., Jr., Tanaka, S. Coupling of rotation and catalysis in F1-ATPase revealed
by single-molecule imaging and manipulation. Cell 130, 309-321 (2007).""",
    """[9] Adachi, K., Oiwa, K., Nishizaka, T., Furuike, S., Noji, H., Itoh, H., et al.
Coupling of rotation and catalysis in F1-ATPase revealed by single-molecule imaging
and manipulation. Cell 130, 309-321 (2007).""")

# --- V37/V38 journal abbreviation and DOI as URL ------------------------
sub('V37+V38',
    """I. Anisotropic fluctuations of amino acids in protein structures. Biophysical Journal
80, 505-515 (2001). doi:10.1016/S0006-3495(01)76033-X""",
    """I. Anisotropic fluctuations of amino acids in protein structures. Biophys. J.
80, 505-515 (2001). https://doi.org/10.1016/S0006-3495(01)76033-X""")

pathlib.Path('data/manuscripts/MS-B.md').write_text(t)
print('MS-B written:', len(t), 'chars,', len(t.split()), 'words')

# ---------------------------------------------------------------------------
# Post-pass (both manuscripts): move the Tables / Figure legends / file lists /
# Supplementary / Graphical-abstract-caption block to AFTER the Reference list.
# In the Word template these live in the body, but in this plain-text rendering
# their position between Acknowledgements and References would be a spurious
# order violation. Moving them to the end in BOTH files keeps the only
# order-related difference the intended one (V13).
# ---------------------------------------------------------------------------
def move_material_block(path):
    s = pathlib.Path(path).read_text()
    i = s.index('\nTables\n')
    j = s.index('\nReferences\n')
    if i > j:
        print('material block already at end:', path); return
    block = s[i:j]
    s = s[:i] + s[j:]
    s = s.rstrip() + '\n\n' + block.strip() + '\n'
    pathlib.Path(path).write_text(s)
    print('material block moved to end:', path)

for p in ('data/manuscripts/MS-A.md', 'data/manuscripts/MS-B.md'):
    move_material_block(p)


