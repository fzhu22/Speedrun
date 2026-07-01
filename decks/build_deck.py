#!/usr/bin/env python3
"""Build the Speedrun MCAT demo/test deck.

Content is DERIVED from *The WikiPremed MCAT Course* by John Wetzel
(https://www.wikipremed.com/), whose course text is published under
Creative Commons Attribution-NonCommercial-ShareAlike (CC BY-NC-SA).
Per ShareAlike, this derived deck is likewise licensed CC BY-NC-SA and is
intended for NON-COMMERCIAL testing/demo use only. Every card carries its
WikiPremed source topic + URL in a dedicated Source field (named-source rule).

Off-MCAT advanced terms (relativity, particle physics, etc.) were intentionally
excluded. The page titled "Enzymes" (code 040103) on WikiPremed contains
nucleic-acids content, so it is labeled "Nucleic Acids" here for accuracy.

Run:  uv run --no-project --with genanki python decks/build_deck.py
"""

import csv
import os

import genanki

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_APKG = os.path.join(HERE, "speedrun_mcat_demo.apkg")
OUT_CSV = os.path.join(HERE, "speedrun_mcat_demo.csv")

DECK_BASE = "Speedrun MCAT Demo (WikiPremed CC BY-NC-SA)"

# (term, definition, section, topic, source_url)
U = {
    "wep": "https://www.wikipremed.com/mcat_course_code-010103.html",
    "mod": "https://www.wikipremed.com/mcat_course_code-010601.html",
    "ab": "https://www.wikipremed.com/mcat_course_code-021200.html",
    "aa": "https://www.wikipremed.com/mcat_course_code-040101.html",
    "na": "https://www.wikipremed.com/mcat_course_code-040103.html",
    "ns": "https://www.wikipremed.com/mcat_course_code-040701.html",
}

CP = "Chem/Phys"
BB = "Bio/Biochem"
PS = "Psych/Soc"

CARDS = [
    # --- Chem/Phys : Work, Energy & Power ---
    ("Energy", "The capacity of one system to do (or be able to do) work on another system.", CP, "Work, Energy & Power", U["wep"]),
    ("Kinetic energy", "The energy an object possesses due to its motion; the work needed to accelerate it from rest to its current speed.", CP, "Work, Energy & Power", U["wep"]),
    ("Potential energy", "Energy stored within a physical system due to position or configuration.", CP, "Work, Energy & Power", U["wep"]),
    ("Mechanical work", "The amount of energy transferred by a force acting over a distance.", CP, "Work, Energy & Power", U["wep"]),
    ("Conservation of energy", "The total energy of an isolated system remains constant, although it may change forms.", CP, "Work, Energy & Power", U["wep"]),
    ("Power", "The rate at which work is performed or energy is transferred (energy per unit time).", CP, "Work, Energy & Power", U["wep"]),
    ("Joule", "The SI unit of energy.", CP, "Work, Energy & Power", U["wep"]),
    ("Watt", "The SI unit of power, equal to one joule per second.", CP, "Work, Energy & Power", U["wep"]),
    ("Conservative force", "A force that does zero net work on a particle that travels along any closed path.", CP, "Work, Energy & Power", U["wep"]),
    ("Mechanical advantage", "The factor by which a mechanism multiplies the input force.", CP, "Work, Energy & Power", U["wep"]),
    ("Electronvolt", "A unit of energy equal to the kinetic energy gained by one electron accelerated through a potential difference of one volt.", CP, "Work, Energy & Power", U["wep"]),

    # --- Chem/Phys : Modern Physics & Atomic Theory ---
    ("Photoelectric effect", "A quantum phenomenon in which electrons are emitted from matter after absorbing energy from electromagnetic radiation.", CP, "Modern Physics & Atomic Theory", U["mod"]),
    ("Work function", "The minimum energy needed to remove an electron from a solid to a point just outside its surface.", CP, "Modern Physics & Atomic Theory", U["mod"]),
    ("Planck constant", "A physical constant that sets the scale of quanta and relates a photon's energy to its frequency; central to quantum mechanics.", CP, "Modern Physics & Atomic Theory", U["mod"]),
    ("de Broglie hypothesis", "The statement that all matter has a wave-like nature (wave-particle duality).", CP, "Modern Physics & Atomic Theory", U["mod"]),
    ("Heisenberg uncertainty principle", "There is a lower bound on the product of the uncertainties in a particle's position and momentum; both cannot be arbitrarily well-defined at once.", CP, "Modern Physics & Atomic Theory", U["mod"]),
    ("Compton scattering", "The decrease in energy (increase in wavelength) of an X-ray or gamma-ray photon when it scatters off matter.", CP, "Modern Physics & Atomic Theory", U["mod"]),
    ("Mass-energy equivalence", "The concept that any mass has an associated energy and vice versa (E = mc^2).", CP, "Modern Physics & Atomic Theory", U["mod"]),
    ("Planck's law", "Describes the spectral radiance of electromagnetic radiation emitted by a blackbody at a given temperature.", CP, "Modern Physics & Atomic Theory", U["mod"]),
    ("Electron diffraction", "A technique that studies matter by firing electrons at a sample and observing the resulting interference pattern (evidence of electron wave nature).", CP, "Modern Physics & Atomic Theory", U["mod"]),
    ("Quantum theory", "The branch of physics based on quantization, begun in 1900 when Planck explained the emission spectrum of black bodies.", CP, "Modern Physics & Atomic Theory", U["mod"]),

    # --- Chem/Phys : Acids & Bases ---
    ("Acid", "A compound that, dissolved in water, gives a solution with pH below 7; more generally, a proton donor.", CP, "Acids & Bases", U["ab"]),
    ("Base", "A substance that can accept protons.", CP, "Acids & Bases", U["ab"]),
    ("pH", "A measure of the acidity or alkalinity of a solution.", CP, "Acids & Bases", U["ab"]),
    ("Strong acid", "An acid that dissociates completely in aqueous solution.", CP, "Acids & Bases", U["ab"]),
    ("Weak acid", "An acid that does not ionize in solution to a significant extent.", CP, "Acids & Bases", U["ab"]),
    ("Weak base", "A base that does not ionize fully in aqueous solution.", CP, "Acids & Bases", U["ab"]),
    ("Lewis acid", "A species that can accept a pair of electrons to form a coordinate covalent bond.", CP, "Acids & Bases", U["ab"]),
    ("Lewis base", "A species that can donate a pair of electrons to form a coordinate covalent bond.", CP, "Acids & Bases", U["ab"]),
    ("Acid dissociation constant (Ka)", "The equilibrium constant for the dissociation of a weak acid.", CP, "Acids & Bases", U["ab"]),
    ("Buffer solution", "A solution that resists changes in pH upon addition of small amounts of acid or base, or upon dilution.", CP, "Acids & Bases", U["ab"]),
    ("Acid-base titration", "A volumetric method to determine the concentration of an unknown acid or base via a neutralization reaction.", CP, "Acids & Bases", U["ab"]),
    ("Equivalence point", "The point in a titration where the amount of titrant added equals the amount of analyte present.", CP, "Acids & Bases", U["ab"]),
    ("Neutralization", "A reaction in which an acid and a base react to produce a salt and water.", CP, "Acids & Bases", U["ab"]),
    ("Hydronium", "The cation (H3O+) derived from protonation of water.", CP, "Acids & Bases", U["ab"]),

    # --- Bio/Biochem : Amino Acids & Protein Structure ---
    ("Amino acid", "A molecule containing both amine and carboxyl functional groups; the building block of proteins.", BB, "Amino Acids & Protein Structure", U["aa"]),
    ("Peptide bond", "The bond formed when the carboxyl group of one amino acid reacts with the amino group of another, releasing water.", BB, "Amino Acids & Protein Structure", U["aa"]),
    ("Protein", "A large polymer of amino acids joined in a linear chain by peptide bonds.", BB, "Amino Acids & Protein Structure", U["aa"]),
    ("Primary structure", "The exact amino-acid sequence of a protein, including its atoms, bonds, and stereochemistry.", BB, "Amino Acids & Protein Structure", U["aa"]),
    ("Secondary structure", "The local three-dimensional forms of segments of a protein, such as alpha helices and beta sheets.", BB, "Amino Acids & Protein Structure", U["aa"]),
    ("Tertiary structure", "The overall three-dimensional structure of a single protein molecule.", BB, "Amino Acids & Protein Structure", U["aa"]),
    ("Quaternary structure", "The arrangement of multiple folded protein subunits in a multi-subunit complex.", BB, "Amino Acids & Protein Structure", U["aa"]),
    ("Alpha helix", "A common secondary-structure motif: a right-handed coil in which each backbone N-H hydrogen-bonds to the carbonyl four residues earlier.", BB, "Amino Acids & Protein Structure", U["aa"]),
    ("Beta sheet", "A secondary structure of strands connected laterally by hydrogen bonds into a pleated sheet.", BB, "Amino Acids & Protein Structure", U["aa"]),
    ("Active site", "The region of an enzyme that contains the catalytic and binding sites.", BB, "Amino Acids & Protein Structure", U["aa"]),
    ("Competitive inhibition", "Enzyme inhibition in which the inhibitor binds the active site and prevents substrate binding (apparent Km rises; Vmax unchanged).", BB, "Amino Acids & Protein Structure", U["aa"]),
    ("Non-competitive inhibition", "Inhibition that lowers the maximum rate (Vmax) without changing the substrate's apparent binding affinity (Km).", BB, "Amino Acids & Protein Structure", U["aa"]),
    ("Isoelectric point", "The pH at which a molecule carries no net electrical charge.", BB, "Amino Acids & Protein Structure", U["aa"]),
    ("Zwitterion", "A molecule that is electrically neutral overall but carries both positive and negative formal charges on different atoms.", BB, "Amino Acids & Protein Structure", U["aa"]),
    ("Disulfide bond", "A covalent bond formed by coupling two thiol groups; stabilizes protein tertiary structure.", BB, "Amino Acids & Protein Structure", U["aa"]),

    # --- Bio/Biochem : Nucleic Acids ---
    ("DNA", "A nucleic acid that contains the genetic instructions used in the development and functioning of living organisms.", BB, "Nucleic Acids", U["na"]),
    ("RNA", "A nucleic acid polymer of nucleotides that helps translate genetic information from DNA into proteins.", BB, "Nucleic Acids", U["na"]),
    ("Nucleotide", "A compound consisting of a nitrogenous base, a sugar, and one or more phosphate groups.", BB, "Nucleic Acids", U["na"]),
    ("Nucleoside", "A nitrogenous base attached to a ribose or deoxyribose sugar (no phosphate group).", BB, "Nucleic Acids", U["na"]),
    ("Base pair", "Two complementary nucleotides on opposite nucleic-acid strands joined by hydrogen bonds.", BB, "Nucleic Acids", U["na"]),
    ("Purine", "A double-ring nitrogenous base (adenine and guanine).", BB, "Nucleic Acids", U["na"]),
    ("Pyrimidine", "A single-ring nitrogenous base (cytosine, thymine, and uracil).", BB, "Nucleic Acids", U["na"]),
    ("Messenger RNA (mRNA)", "An RNA molecule encoding the chemical blueprint for a protein product.", BB, "Nucleic Acids", U["na"]),
    ("Transfer RNA (tRNA)", "A small RNA that delivers a specific amino acid to the ribosome during translation.", BB, "Nucleic Acids", U["na"]),
    ("Ribosomal RNA (rRNA)", "RNA synthesized in the nucleolus that is the central component of the ribosome.", BB, "Nucleic Acids", U["na"]),
    ("Adenosine triphosphate (ATP)", "A nucleotide that serves as the main molecular currency of intracellular energy transfer.", BB, "Nucleic Acids", U["na"]),
    ("Chromatin", "The complex of DNA and protein that makes up chromosomes.", BB, "Nucleic Acids", U["na"]),
    ("Histone", "A chief protein component of chromatin, acting as a spool around which DNA winds and playing a role in gene regulation.", BB, "Nucleic Acids", U["na"]),
    ("Complementarity", "The property of double-stranded nucleic acids in which base pairs form between strands via hydrogen bonds.", BB, "Nucleic Acids", U["na"]),

    # --- Psych/Soc (Biological foundations of behavior) : Nervous System ---
    ("Neuron", "An electrically excitable cell that processes and transmits information in the nervous system.", PS, "Nervous System", U["ns"]),
    ("Central nervous system", "The largest part of the nervous system, comprising the brain and the spinal cord.", PS, "Nervous System", U["ns"]),
    ("Peripheral nervous system", "The part of the nervous system outside the brain and spinal cord, serving the limbs and organs.", PS, "Nervous System", U["ns"]),
    ("Action potential", "A spike of electrical discharge that travels along the membrane of a cell.", PS, "Nervous System", U["ns"]),
    ("Resting potential", "The membrane potential of a cell when there are no action potentials or other active changes.", PS, "Nervous System", U["ns"]),
    ("Membrane potential", "The electrical voltage across a cell's plasma membrane.", PS, "Nervous System", U["ns"]),
    ("Depolarization", "A decrease in the absolute value of a cell's membrane potential.", PS, "Nervous System", U["ns"]),
    ("Sympathetic nervous system", "The branch of the autonomic nervous system that becomes more active during stress (fight-or-flight).", PS, "Nervous System", U["ns"]),
    ("Parasympathetic nervous system", "The autonomic branch that, in opposition to the sympathetic system, governs rest-and-digest functions.", PS, "Nervous System", U["ns"]),
    ("Somatic nervous system", "The peripheral branch associated with voluntary control of body movement and reception of external stimuli.", PS, "Nervous System", U["ns"]),
    ("Autonomic nervous system", "The peripheral branch that acts as a control system maintaining homeostasis (involuntary).", PS, "Nervous System", U["ns"]),
    ("Neurotransmitter", "A chemical used to relay, amplify, and modulate signals between a neuron and another cell.", PS, "Nervous System", U["ns"]),
    ("Chemical synapse", "A specialized junction where neurons use neurotransmitters to signal to other cells.", PS, "Nervous System", U["ns"]),
    ("Myelin", "An electrically insulating phospholipid layer that surrounds the axons of many neurons.", PS, "Nervous System", U["ns"]),
    ("Saltatory conduction", "The means by which action potentials are transmitted along myelinated fibers, jumping between nodes of Ranvier.", PS, "Nervous System", U["ns"]),
    ("Acetylcholine", "The first neurotransmitter identified; acts in both the peripheral and central nervous systems (e.g., at the neuromuscular junction).", PS, "Nervous System", U["ns"]),
    ("Fight-or-flight response", "An animal's reaction to a threat via a general discharge of the sympathetic nervous system.", PS, "Nervous System", U["ns"]),
]

SECTION_META = {
    CP: {"suffix": "Chem-Phys", "tag": "ChemPhys", "deck_id": 1980000001},
    BB: {"suffix": "Bio-Biochem", "tag": "BioBiochem", "deck_id": 1980000002},
    PS: {"suffix": "Psych-Soc", "tag": "PsychSoc", "deck_id": 1980000003},
}


def tagify(text: str) -> str:
    out = []
    for ch in text:
        if ch.isalnum():
            out.append(ch)
        elif ch in " -/&":
            out.append("_")
    token = "".join(out)
    while "__" in token:
        token = token.replace("__", "_")
    return token.strip("_")


MODEL = genanki.Model(
    1980530001,
    "Speedrun Basic + Source",
    fields=[{"name": "Front"}, {"name": "Back"}, {"name": "Source"}],
    templates=[
        {
            "name": "Card 1",
            "qfmt": '<div class="term">{{Front}}</div>',
            "afmt": '{{FrontSide}}<hr id="answer"><div class="def">{{Back}}</div>'
                    '<div class="src">{{Source}}</div>',
        }
    ],
    css=(
        ".card{font-family:-apple-system,Segoe UI,Roboto,sans-serif;font-size:20px;"
        "text-align:center;color:#1a1a1a;background:#fff;padding:18px}"
        ".term{font-weight:600}.def{margin-top:8px}"
        ".src{margin-top:16px;color:#8a8a8a;font-size:12px}"
    ),
)


def build():
    decks = {}
    for section, meta in SECTION_META.items():
        decks[section] = genanki.Deck(meta["deck_id"], f"{DECK_BASE}::{meta['suffix']}")

    counts = {CP: 0, BB: 0, PS: 0}
    rows = []
    for term, definition, section, topic, url in CARDS:
        meta = SECTION_META[section]
        source = f"WikiPremed (CC BY-NC-SA) - {topic} - {url}"
        tags = [
            f"MCAT::{meta['tag']}",
            f"MCAT::{meta['tag']}::{tagify(topic)}",
            "source::WikiPremed",
        ]
        note = genanki.Note(
            model=MODEL,
            fields=[term, definition, source],
            tags=tags,
            guid=genanki.guid_for("speedrun-wikipremed", term),
        )
        decks[section].add_note(note)
        counts[section] += 1
        rows.append([term, definition, source, " ".join(tags)])

    genanki.Package(list(decks.values())).write_to_file(OUT_APKG)

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Front", "Back", "Source", "Tags"])
        w.writerows(rows)

    total = sum(counts.values())
    print(f"Built {OUT_APKG}")
    print(f"Built {OUT_CSV}")
    print(f"Total cards: {total}")
    for section, n in counts.items():
        print(f"  {section}: {n}")


if __name__ == "__main__":
    build()
