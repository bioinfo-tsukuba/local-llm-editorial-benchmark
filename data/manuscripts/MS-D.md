[Submitted to Biophysics and Physicobiology — Regular Article]
[Manuscript ID: BPPB-2026-0513]

Running title: Allosteric coupling in ring ATPases

A coarse-grained model of allosteric communication in a ring-shaped ATPase

Kenji Morisawa (1), Aiko Terashima (1), Ryo Nishimura (2), Sarah J. Whitfield (3), Hideo Kuramoto (1,*)

(1) Department of Molecular Biophysics, Kitagawa Institute of Technology, Kyoto, Japan
(2) Laboratory for Computational Cell Dynamics, Nanto University, Nanto, Japan
(3) Department of Physics, University of Ellesmere, Ellesmere, United Kingdom

*Corresponding author: Hideo Kuramoto, Department of Molecular Biophysics,
Kitagawa Institute of Technology, 3-14-2 Nishikyogoku, Ukyo-ku, Kyoto 615-0882, Japan
ORCID iD: https://orcid.org/0000-0002-1825-0097
E-mail: kuramoto@kit-mb.example.ac.jp

Abstract

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

Keywords: elastic network model, allostery, ring ATPase, normal mode analysis, Brownian dynamics

Significance

Understanding how the subunits of a ring-shaped ATPase coordinate their catalytic
cycles is a long-standing problem in biophysics. This study introduces a
coarse-grained elastic network model in which the nucleotide state of each subunit can
be switched independently, making it possible to map the directionality of allosteric
communication around the ring at low computational cost. The communication channel is
strongly asymmetric and is carried by a small number of contacts near the C-terminal
helix, a prediction that can be tested by truncation experiments.

Introduction

The interconversion of chemical and mechanical free energy by protein assemblies is a
central theme of molecular biophysics. Ring-shaped ATPases such as the F1 sector of
ATP synthase, the AAA+ unfoldases, and the hexameric helicases all share a common
architectural motif: several nominally identical catalytic subunits arranged in a
closed ring, with the nucleotide binding pockets located at the subunit interfaces
[1,2]. Because the pockets are shared between neighbours, the chemical state of one
subunit is expected to influence the affinity and catalytic rate of its neighbours,
and this coupling is generally invoked to explain the highly ordered firing sequences
observed in single-molecule assays.

Structural studies have provided a large number of static snapshots of ring ATPases in
different nucleotide occupancy states, and these have been extremely valuable in
establishing which conformations are accessible [PDB ID: 6qw9] (https://doi.org/10.2210/pdb6qw9/pdb). What the static picture
does not provide is a quantitative measure of how strongly, and in which direction,
information flows between subunits. All-atom molecular dynamics can in principle answer
this question, but the relevant relaxation times are long compared with what is
routinely accessible, and the statistical uncertainty in a coupling coefficient
extracted from a single trajectory is typically larger than the coefficient itself.

Coarse-grained elastic network models offer a complementary route. Because the
potential is harmonic, the covariance matrix of the fluctuations is available
analytically, and perturbation-response relations can be evaluated without any
sampling at all. The standard objection to elastic network models is that they contain
no chemistry, and therefore cannot represent the effect of nucleotide binding. We
address this objection with a minimal modification: a nucleotide-dependent stiffening
term applied to the P-loop region, whose single parameter is calibrated against the
experimentally measured change in the amide hydrogen exchange rate upon nucleotide
binding [4]. The resulting model is still analytically tractable, yet it distinguishes
apo from nucleotide-bound subunits.

In this paper we apply the model to a hexameric ring, characterize the directionality
of the allosteric channel, and identify the contacts responsible for it. The remainder
of the paper is organized as follows. Materials and methods describes the network
construction, the nucleotide-dependent potential, and the Brownian dynamics protocol.
Results presents the normal mode reorganization, the susceptibility maps, and the
truncation analysis. Discussion places the findings in the context of existing kinetic
models.

Materials and methods

Network construction

Coordinates for the hexameric ring were taken from the deposited structure and
protonated with standard tools. One bead was placed at each alpha-carbon position.
Beads separated by less than a cutoff distance of 12 A were connected by harmonic
springs with a uniform force constant, following the anisotropic network model
convention. Beads belonging to the same subunit and separated by fewer than four
residues along the chain were assigned a threefold larger force constant to represent
covalent and secondary-structure connectivity. The full network for the hexamer
contained 2,934 beads and 66,526 springs (Table 1).

Nucleotide-dependent potential

Springs with at least one endpoint in the P-loop region (residues 158-166 of each
subunit) were multiplied by a stiffening factor s when the corresponding subunit was
designated as nucleotide-bound. The value of s was determined by matching the
predicted change in root-mean-square fluctuation of the P-loop backbone to the change
in amide hydrogen exchange protection measured for the isolated subunit, giving
s = 2.8 +/- 0.4. All results below use s = 2.8 unless stated otherwise. Sensitivity
to s is reported in Table 2.

Normal mode and susceptibility analysis

The Hessian of the network was diagonalized and the six zero-frequency modes were
projected out. The perturbation-response susceptibility between subunits i and j was
defined as the trace of the block of the pseudo-inverse Hessian connecting the two
P-loop regions, normalized by the corresponding diagonal blocks. Effective length
constants were obtained by fitting the susceptibility as a function of subunit
separation to a single exponential.

Brownian dynamics

Overdamped Langevin dynamics were integrated with a time step of 50 ps and a uniform
friction coefficient. The chemical driving protocol switched the nucleotide state of
each subunit in turn with a fixed dwell time, cycling around the ring. Each production
run covered 20 ms and thirty independent runs were performed for each condition.

Single-molecule rotation assay

For comparison with the model we performed rotation assays on the purified enzyme.
Myosin used as a reference standard in the calibration measurements was purified from
rabbit skeletal muscle by the standard procedure. All animal procedures were
approved by the Institutional Animal Care and Use Committee of the Kitagawa
Institute of Technology (approval no. 2025-041) and were carried out in accordance
with its guidelines. Rotation of a 200 nm bead attached to
the central stalk was recorded at 5000 frames per second.

Results

Reorganization of the low-frequency spectrum depends on occupancy pattern

Figure 1 shows the mode displacement fields of the three lowest non-trivial modes,
in which the localization of the shear mode onto the unoccupied side of the ring is
clearly visible for the adjacent pattern. The corresponding frequency spectra for the
three occupancy patterns are shown in Figure 2. The three lowest non-trivial modes of
the fully apo ring are the expected degenerate pair of in-plane shear modes and a
breathing mode. When two adjacent subunits are switched to the bound state the
degeneracy is lifted and the mode ordering changes, whereas the opposite-subunit
pattern leaves the spectrum essentially unchanged.

The susceptibility maps quantifying this behaviour are collected in Table 2, together
with the dependence on the stiffening factor s. Across the range s = 2.0 to 3.6 the
qualitative asymmetry is preserved, and the fitted length constants vary by less than
15%.

Directionality of the allosteric channel

The susceptibility decays with an effective length constant of 2.3 subunits in the
counter-clockwise direction and 0.7 subunits in the clockwise direction (Figure 3).
The asymmetry is not a consequence of the asymmetric occupancy pattern used to probe
it, since reversing the probe subunit reverses the sign of the asymmetry as expected
for a genuine directional channel. We verified that the effect survives when the
cutoff distance is varied between 10 and 14 A, and when the alpha-carbon network is
replaced by a two-bead-per-residue network.

Contacts responsible for directionality

Truncating the C-terminal helix of a single subunit, implemented by deleting the beads
of residues 471-489 and all springs incident on them, reduces the counter-clockwise
length constant to 0.9 subunits while leaving the clockwise value unchanged, so that
the channel becomes nearly isotropic. The equilibrium root-mean-square
fluctuation of the ring as a whole changes by less than 3% under the same truncation,
confirming that the global elastic architecture is not appreciably perturbed. A
residue-level decomposition of the susceptibility change (Figure 4) identifies six
contacts, all
between the C-terminal helix of one subunit and the nucleotide-binding core of its
counter-clockwise neighbour, that together account for 78% of the effect.

Comparison with rotation assays

The sequential firing order predicted by the driven Brownian dynamics matches the order
observed in the rotation assays. The mean rotation rate saturates above a driving
frequency of about 400 s^-1, and the saturation value is within a factor of two of the
measured maximum rate. The measured dwell time distributions are broader than the
simulated ones, which we attribute to heterogeneity between individual molecules
(Terashima, A., unpublished data).

Discussion

The main result of this work is that allosteric communication around a hexameric ring
ATPase can be strongly directional even when the underlying elastic architecture is
nearly symmetric, and that the directionality can be traced to a small number of
specific interfacial contacts. This is consistent with the general expectation from
kinetic models that ordered firing requires a mechanism for breaking the symmetry
between the two neighbours of an occupied subunit, but it locates the symmetry breaking
in the mechanics of the C-terminal helix rather than in the chemistry of the binding
pocket.

Our approach has clear limitations. The elastic network potential cannot describe the
large conformational excursions that accompany the power stroke, and the
nucleotide-dependent stiffening term is a crude representation of a complex chemical
event. The single calibration parameter s was fitted to hydrogen exchange data for the
isolated subunit, and it is not obvious that the same value should apply in the
assembled ring. We have shown that the qualitative conclusions are robust across a
factor of nearly two in s, which is reassuring but not decisive.

The prediction that is most directly testable is the truncation result. Deleting the
C-terminal helix of a single subunit within an otherwise intact ring is experimentally
demanding but not impossible using engineered single-chain constructs, and the
prediction is specific: the firing order should become disordered while the overall
stability of the ring is retained. A similar analysis applied to the chaperonin ring
gives a much weaker asymmetry, which we will report elsewhere [8].

Conclusion

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

References

[1] Boyer, P. D. The ATP synthase - a splendid molecular machine. Annu. Rev. Biochem.
66, 717-749 (1997). https://doi.org/10.1146/annurev.biochem.66.1.717

[2] Erzberger, J. P., Berger, J. M. Evolutionary relationships and structural
mechanisms of AAA+ proteins. Annu. Rev. Biophys. Biomol. Struct. 35, 93-114 (2006).
https://doi.org/10.1146/annurev.biophys.35.040405.101933

[3] Tama, F., Sanejouand, Y. H. Conformational change of proteins arising from normal
mode calculations. Protein Eng. 14, 1-6 (2001). https://doi.org/10.1093/protein/14.1.1

[4] Atilgan, A. R., Durell, S. R., Jernigan, R. L., Demirel, M. C., Keskin, O., Bahar,
I. Anisotropic fluctuations of amino acids in protein structures. Biophys. J.
80, 505-515 (2001). https://doi.org/10.1016/S0006-3495(01)76033-X

[5] Nishimura, R., Morisawa, K. Directional coupling in driven elastic networks.
Biophys. Physicobiol. 22, 41-53 (2025). https://doi.org/10.2142/biophysico.bppb-v22.0041

[6] Togashi, Y., Mikhailov, A. S. Nonlinear relaxation dynamics in elastic networks
and design principles of molecular machines. Proc. Natl. Acad. Sci. U.S.A. 104,
8697-8702 (2007). https://doi.org/10.1073/pnas.0702950104

[7] Ikeguchi, M., Ueno, J., Sato, M., Kidera, A. Protein structural change upon ligand
binding: linear response theory. Phys. Rev. Lett. 94, 078102 (2005).
https://doi.org/10.1103/PhysRevLett.94.078102

[8] Kuramoto, H., Morisawa, K. Elastic network analysis of chaperonin rings.
Biophys. Physicobiol. 23, 8-19 (2026). https://doi.org/10.2142/biophysico.bppb-v23.0008

[9] Adachi, K., Oiwa, K., Nishizaka, T., Furuike, S., Noji, H., Itoh, H., et al.
Coupling of rotation and catalysis in F1-ATPase revealed by single-molecule imaging
and manipulation. Cell 130, 309-321 (2007).
https://doi.org/10.1016/j.cell.2007.05.020

[10] Ichimura, T., Kakizuka, T., Horikawa, K., Seiriki, K., Kasai, A., Hashimoto, H.,
et al. Exploring rare cellular activity in more than one million cells by a
trans-scale-scope. bioRxiv (2020). https://doi.org/10.1101/2020.06.29.179044

[11] Itoh, H., Takahashi, A., Adachi, K., Noji, H., Yasuda, R., Yoshida, M., et al.
Mechanically driven ATP synthesis by F1-ATPase. Nature (in press).

[12] Yasuda, R., Noji, H., Yoshida, M., Kinosita, K., Jr., Itoh, H. Resolution of
distinct rotational substeps by submillisecond kinetic analysis of F1-ATPase. Nature
410, 898-904 (2001). https://doi.org/10.1038/35073513

Tables

  Table 1  Bead and spring counts for the networks used in this study.
  ------------------------------------------------------------------
  Network                Beads     Springs     Cutoff (A)
  ------------------------------------------------------------------
  Hexamer, apo            2934      66526      12
  Hexamer, 2 adjacent     2934      66526      12
  Hexamer, truncated      2915      66051      12
  Monomer                  489      10712      12
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

Figure legends

Figure 1. Mode displacement fields for the three lowest non-trivial normal modes of the
apo ring and of the ring with two adjacent subunits occupied. Arrows show bead
displacements, scaled by a factor of 8 for visibility.

Figure 2. Frequency spectra of the elastic network for the three occupancy patterns
studied. Only the lowest 40 non-trivial modes are shown.

Figure 3. Perturbation-response susceptibility as a function of subunit separation in
the clockwise and counter-clockwise directions, with single-exponential fits.

Figure 4. Residue-level decomposition of the susceptibility change upon C-terminal
helix truncation, shown as a heat map over the subunit interface.

Figure file list
  Fig1_modes.tiff       300 dpi, colour
  Fig2_spectra.tiff     300 dpi, colour
  Fig3_susceptibility.png   600 dpi, greyscale
  Fig4_heatmap.png      600 dpi, colour
  Graphical_abstract.png    300 dpi, colour

Supplementary materials
  Supplementary Figure S1 (SupplementaryFigureS1.pdf)   Convergence of the Brownian dynamics runs
  Supplementary Table S1 (SupplementaryTableS1.xlsx)   Full susceptibility matrices
  Supplementary Movie S1 (SupplementaryMovieS1.mpeg)   Animation of the lowest shear mode (18 MB)

Graphical abstract caption

The elastic network of a hexameric ring ATPase is drawn with one subunit switched to
the nucleotide-bound state, and the arrows show the perturbation-response
susceptibility transmitted to each neighbour. The colour scale indicates the
magnitude of the response, which decays over 2.3 subunits counter-clockwise but only
0.7 subunits clockwise. The inset marks the six interfacial contacts that carry this
asymmetry.
