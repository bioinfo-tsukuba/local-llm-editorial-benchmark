[Submitted to Biophysics and Physicobiology — Commentary and Perspective]
[Manuscript ID: BPPB-2026-0603]

Novel directions for coarse-grained models of molecular machines

Hideo Kuramoto (1,*), Aiko Terashima (1)

(1) Department of Molecular Biophysics, Kitagawa Institute of Technology, Kyoto, Japan

*Corresponding author: Hideo Kuramoto, Department of Molecular Biophysics,
Kitagawa Institute of Technology, 3-14-2 Nishikyogoku, Ukyo-ku, Kyoto 615-0882, Japan
ORCID iD: https://orcid.org/0000-0002-1825-0097
E-mail: kuramoto@kit-mb.example.ac.jp

Keywords: elastic network model, allostery, molecular machine

Introduction

The 2026 Annual Meeting of the Biophysical Society of Japan devoted an unusual amount of
programme time to coarse-grained modelling of molecular machines, and the discussion in
those sessions was more contentious than the published literature would suggest. This
Commentary sets out what we take to be the substance of the disagreement, and why we
think it will not be settled by producing more models.

The point of contention is not whether coarse-grained elastic network models are useful.
Everyone agrees that they are, and the reason is well understood: because the potential
is harmonic, the covariance matrix of the fluctuations is available in closed form, and
perturbation-response relations can be evaluated without any sampling (1, 2). For a
question such as "which residues transmit a conformational signal from this pocket to
that one", the method gives an answer in minutes on a laptop where an all-atom
trajectory would take months and still carry a statistical uncertainty larger than the
quantity being estimated.

The disagreement is about what such an answer means.

Two readings of an elastic network result

One camp treats the elastic network as a caricature whose predictions are qualitative
statements about topology. On this reading, a computed susceptibility map identifies
which contacts matter, and the numerical value attached to each contact is not to be
taken seriously. The model has done its job when it produces a testable hypothesis, and
the hypothesis is tested by mutagenesis, not by a better calculation.

The other camp treats the numbers as estimates. If a susceptibility decays with a length
constant of 2.3 subunits in one direction and 0.7 in the other, that asymmetry is a
prediction about a measurable quantity, and a factor of three is either right or wrong.
On this reading the harmonic approximation is a controlled approximation, and the task
is to bound its error.

We think the first reading is the defensible one at present, and that the second is
where the field would like to be. The gap between them is not a matter of taste. It is
that nobody has produced an error estimate for an elastic network prediction that
survives contact with an independent measurement. Papers that report a length constant
to two significant figures almost never report what would change if the cutoff distance
were altered by twenty per cent, and the few that do tend to find that it changes a
lot [4].

What would close the gap

Three things, in our view.

First, the community needs benchmark systems where the answer is known independently and
the geometry is not in dispute. The chaperonin ring is a plausible candidate, and so are
the hexameric helicases, but in both cases the nucleotide occupancy of the reference
structure is itself contested, which defeats the purpose.

Second, sensitivity analysis needs to become a reporting requirement rather than a
courtesy. It is not expensive: the whole point of a harmonic model is that the
susceptibility is a closed-form function of the spring constants, so scanning a
parameter costs a matrix inversion. A journal could ask for it as a matter of course.

Third, and least comfortably, the field needs to be honest about the fact that adding
chemistry to an elastic network is not a small modification. A nucleotide-dependent
stiffening term with a single fitted parameter is a reasonable device, and we have used
one ourselves [7], but it is a device. The moment one asks how the fitted value transfers
from an isolated subunit to an assembled ring, the harmonic framework stops giving
answers and starts requiring assumptions.

A note on the alternative

It is sometimes argued that machine-learned potentials will make this discussion
obsolete. We are sceptical, for a reason that has nothing to do with the quality of the
potentials. The attraction of an elastic network is that one can see why it gives the
answer it gives: the susceptibility is a sum over paths through a contact graph, and the
dominant paths can be enumerated and inspected. A learned potential that reproduces the
same susceptibility more accurately does not thereby explain it. For the questions that
motivate this literature, interpretability is not a secondary consideration; it is the
product.

Outlook

The honest summary of the present position is that coarse-grained elastic network models
are an excellent hypothesis-generating tool whose quantitative claims are not yet
calibrated. That is not a criticism. It is a description of a field at a particular
stage, and it suggests where effort is best spent. Our own guess is that the next real
advance will come not from a more elaborate potential but from a benchmark that the
whole community accepts, and that the work of assembling such a benchmark is less
glamorous and more valuable than another model.

Conflict of interest

H.K. and A.T. declare that they have no conflict of interest.

Author contributions

H.K. and A.T. discussed the content and co-wrote the manuscript.

Data availability

No new data were generated for this Commentary. The susceptibility calculations
referred to in the text are available from the corresponding author on reasonable
request.

Acknowledgements

We thank the organizers of the 2026 Annual Meeting of the Biophysical Society of Japan
for the invitation that prompted this Commentary, and the participants of the
coarse-graining session for a frank discussion.

References

[1] Tama, F., Sanejouand, Y. H. Conformational change of proteins arising from normal
mode calculations. Protein Eng. 14, 1-6 (2001). https://doi.org/10.1093/protein/14.1.1

[2] Atilgan, A. R., Durell, S. R., Jernigan, R. L., Demirel, M. C., Keskin, O., Bahar,
I. Anisotropic fluctuations of amino acids in protein structures. Biophys. J. 80,
505-515 (2001). https://doi.org/10.1016/S0006-3495(01)76033-X

[3] Ikeguchi, M., Ueno, J., Sato, M., Kidera, A. Protein structural change upon ligand
binding: linear response theory. Phys. Rev. Lett. 94, 078102 (2005).
https://doi.org/10.1103/PhysRevLett.94.078102

[4] Erzberger, J. P., Berger, J. M. Evolutionary relationships and structural
mechanisms of AAA+ proteins. Annu. Rev. Biophys. Biomol. Struct. 35, 93-114 (2006).
https://doi.org/10.1146/annurev.biophys.35.040405.101933

[5] Terashima, A., Kuramoto, H. Benchmarks for coarse-grained allostery. In preparation.

[7] Kuramoto, H., Morisawa, K. Elastic network analysis of chaperonin rings.
Biophys. Physicobiol. 23, 8-19 (2026). https://doi.org/10.2142/biophysico.bppb-v23.0008

[6] Togashi, Y., Mikhailov, A. S. Nonlinear relaxation dynamics in elastic networks
and design principles of molecular machines. Proc. Natl. Acad. Sci. U.S.A. 104,
8697-8702 (2007). https://doi.org/10.1073/pnas.0702950104

[8] Oosawa, F., Asakura, S. Thermodynamics of the Polymerization of Proteins (Academic
Press, New York, 1975).

Tables

  Table 1  Reported sensitivity of published elastic network susceptibilities to the
  contact cutoff distance.
  ------------------------------------------------------------------
  Study                | Cutoff varied (A) | Change in length constant
  ------------------------------------------------------------------
  Ref. [1]             | not reported      | not reported
  Ref. [3]             | 10-14             | 15%
  Ref. [4]             | 8-16              | 60%
  Ref. [7]             | 10-14             | 12%
  ------------------------------------------------------------------

Figure legends

Figure 1. Two readings of an elastic network susceptibility map. Left: the topological
reading, in which only the ranking of contacts is taken to be meaningful. Right: the
quantitative reading, in which the decay length is treated as an estimate of a
measurable quantity.

Figure file list
  Fig1_two_readings.bmp   150 dpi, colour

Supplementary materials
  Supplementary Text S1 (SupplementaryTextS1.pdf)   Notes on the meeting discussion
  図1_draft version.bmp   Earlier version of Figure 1
