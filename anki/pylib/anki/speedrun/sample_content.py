"""Original, clearly-labeled sample MCAT content (no copyrighted stems).

There is no openly-licensed, MCAT-appropriate flashcard set that can ship in an
AGPL repo (AnKing/MileDown are copyrighted; Khan Academy is CC BY-NC-SA; MedMCQA is
a different exam). So this is original `[Sample]` content keyed by AAMC content
category - enough to make coverage, memory, and the fading ladder real to test.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

#: content-category code -> [(front, back), ...]
SAMPLE_CARDS: Dict[str, List[Tuple[str, str]]] = {
    "1A": [
        ("[Sample] How many standard (proteinogenic) amino acids are there?", "20"),
        ("[Sample] What bond links amino acids in a peptide?", "Peptide (amide) bond"),
        ("[Sample] An alpha-helix is which level of protein structure?", "Secondary structure"),
    ],
    "1B": [
        ("[Sample] Which enzyme synthesizes mRNA from a DNA template?", "RNA polymerase"),
        ("[Sample] Where does eukaryotic translation occur?", "The ribosome"),
        ("[Sample] What is the start codon?", "AUG (methionine)"),
    ],
    "1C": [
        ("[Sample] Which meiotic process exchanges DNA between homologs?", "Crossing over (recombination)"),
        ("[Sample] A change in a single DNA base is what kind of mutation?", "Point mutation"),
        ("[Sample] How many chromosomes are in a diploid human somatic cell?", "46"),
    ],
    "1D": [
        ("[Sample] Net ATP produced by glycolysis per glucose?", "2 ATP"),
        ("[Sample] Where does the citric acid cycle occur?", "Mitochondrial matrix"),
        ("[Sample] Final electron acceptor in the electron transport chain?", "Oxygen (O2)"),
    ],
    "2A": [
        ("[Sample] Which organelle modifies and packages proteins for secretion?", "Golgi apparatus"),
        ("[Sample] What model describes the cell membrane?", "Fluid mosaic model"),
        ("[Sample] Site of aerobic respiration in the cell?", "Mitochondrion"),
    ],
    "2B": [
        ("[Sample] Do prokaryotes have a membrane-bound nucleus?", "No"),
        ("[Sample] A virus that infects bacteria is called a?", "Bacteriophage"),
        ("[Sample] Bacterial cell walls are made primarily of?", "Peptidoglycan"),
    ],
    "2C": [
        ("[Sample] In which phase of mitosis do sister chromatids separate?", "Anaphase"),
        ("[Sample] Programmed cell death is called?", "Apoptosis"),
        ("[Sample] Unspecialized cells that can become many cell types are?", "Stem cells"),
    ],
    "3A": [
        ("[Sample] Which neuron part receives incoming signals?", "Dendrite"),
        ("[Sample] Which gland secretes insulin?", "Pancreas (beta cells)"),
        ("[Sample] Neurotransmitter at the neuromuscular junction?", "Acetylcholine"),
    ],
    "3B": [
        ("[Sample] Which side of the heart pumps blood to the lungs?", "Right side"),
        ("[Sample] The functional unit of the kidney is the?", "Nephron"),
        ("[Sample] Gas exchange in the lungs occurs in the?", "Alveoli"),
    ],
    "4A": [
        ("[Sample] SI unit of force?", "Newton (N)"),
        ("[Sample] Kinetic energy formula?", "KE = 1/2 m v^2"),
        ("[Sample] Newton's second law?", "F = ma"),
    ],
    "4B": [
        ("[Sample] Hydrostatic pressure at depth h?", "P = rho g h"),
        ("[Sample] For an ideal fluid, A x v along a tube is?", "Constant (continuity)"),
        ("[Sample] Upward force on a submerged object is?", "Buoyant force"),
    ],
    "4C": [
        ("[Sample] Ohm's law?", "V = IR"),
        ("[Sample] In a series circuit, current across elements is?", "The same"),
        ("[Sample] Oxidation is the loss or gain of electrons?", "Loss"),
    ],
    "4D": [
        ("[Sample] Approximate wavelength range of visible light?", "~400-700 nm"),
        ("[Sample] Bending of light as it changes media is?", "Refraction"),
        ("[Sample] Sound travels fastest in solids, liquids, or gases?", "Solids"),
    ],
    "4E": [
        ("[Sample] Which nuclear particle carries a +1 charge?", "Proton"),
        ("[Sample] Beta-minus decay converts a neutron into a?", "Proton (emitting an electron)"),
        ("[Sample] Max electrons in the n=2 shell?", "8"),
    ],
    "5A": [
        ("[Sample] pH of a neutral solution at 25C?", "7"),
        ("[Sample] Water's high boiling point is due to?", "Hydrogen bonding"),
        ("[Sample] pH + pOH at 25C equals?", "14"),
    ],
    "5B": [
        ("[Sample] Strongest intermolecular force among neutral molecules?", "Hydrogen bonding"),
        ("[Sample] London dispersion forces arise from?", "Temporary (induced) dipoles"),
        ("[Sample] Compounds with the same formula but different structure are?", "Isomers"),
    ],
    "5C": [
        ("[Sample] Technique separating liquids by boiling point?", "Distillation"),
        ("[Sample] Chromatography separates based on?", "Differential affinity (partitioning)"),
        ("[Sample] Gel electrophoresis separates molecules using?", "An electric field"),
    ],
    "5D": [
        ("[Sample] Joining monomers while releasing water is?", "Dehydration (condensation) synthesis"),
        ("[Sample] A carbonyl carbon is attacked by a?", "Nucleophile"),
        ("[Sample] Carboxylic acid + alcohol yields an?", "Ester"),
    ],
    "5E": [
        ("[Sample] Sign of dG for a spontaneous process?", "Negative"),
        ("[Sample] What does a catalyst do to activation energy?", "Lowers it"),
        ("[Sample] In dG = dH - T dS, what is T?", "Absolute temperature (Kelvin)"),
    ],
    "6A": [
        ("[Sample] Converting a stimulus into a neural signal is?", "Transduction"),
        ("[Sample] The minimum stimulus detectable 50% of the time is the?", "Absolute threshold"),
        ("[Sample] Retinal photoreceptors for color are?", "Cones"),
    ],
    "6B": [
        ("[Sample] Principles of grouping visual elements are the?", "Gestalt principles"),
        ("[Sample] Memory lasting ~20-30 seconds is?", "Short-term memory"),
        ("[Sample] A mental shortcut in decision-making is a?", "Heuristic"),
    ],
    "6C": [
        ("[Sample] Fight-or-flight is driven by which nervous system?", "Sympathetic nervous system"),
        ("[Sample] The James-Lange theory says emotion follows?", "Physiological arousal"),
        ("[Sample] Hormone released by the adrenal medulla in stress?", "Epinephrine (adrenaline)"),
    ],
    "7A": [
        ("[Sample] Learning by associating two stimuli is?", "Classical conditioning"),
        ("[Sample] Increasing behavior by removing an aversive stimulus is?", "Negative reinforcement"),
        ("[Sample] Stable pattern of thoughts/behavior across situations is?", "Personality"),
    ],
    "7B": [
        ("[Sample] Better performance on simple tasks when observed is?", "Social facilitation"),
        ("[Sample] Loss of self-awareness in a group is?", "Deindividuation"),
        ("[Sample] Yielding to group pressure is?", "Conformity"),
    ],
    "7C": [
        ("[Sample] Tension from conflicting attitudes and behavior is?", "Cognitive dissonance"),
        ("[Sample] Persuasion via logical argument uses which route?", "Central route"),
        ("[Sample] Starting with a small request to gain a larger one is?", "Foot-in-the-door"),
    ],
    "8A": [
        ("[Sample] Belief in one's ability to succeed at a task is?", "Self-efficacy"),
        ("[Sample] Our overall evaluation of self-worth is?", "Self-esteem"),
        ("[Sample] Whose stages include trust vs. mistrust?", "Erikson"),
    ],
    "8B": [
        ("[Sample] Overattributing others' behavior to disposition is the?", "Fundamental attribution error"),
        ("[Sample] An oversimplified belief about a group is a?", "Stereotype"),
        ("[Sample] Besides affective and behavioral, the third attitude component is?", "Cognitive"),
    ],
    "8C": [
        ("[Sample] Controlling the impression others form of us is?", "Impression management"),
        ("[Sample] Reduced helping when others are present is the?", "Bystander effect"),
        ("[Sample] Expected behaviors for a social position make up a?", "Role"),
    ],
    "9A": [
        ("[Sample] The scientific study of society is?", "Sociology"),
        ("[Sample] A large group organized to pursue goals is a?", "Formal organization"),
        ("[Sample] Durkheim's term for social cohesion is social?", "Solidarity"),
    ],
    "9B": [
        ("[Sample] The statistical study of populations is?", "Demography"),
        ("[Sample] Movement of people into a region is?", "Immigration"),
        ("[Sample] The shift from high to low birth/death rates is the?", "Demographic transition"),
    ],
    "10A": [
        ("[Sample] Unequal distribution of resources is social?", "Stratification"),
        ("[Sample] Difficulty moving between social classes is low social?", "Mobility"),
        ("[Sample] Unequal access to care by group is a health?", "Disparity"),
    ],
}

#: Seed disconfirmer cards so the fading ladder has data. Each maps onto a family;
#: some are flagged as transfer (held-out) items, which the fade rule needs.
DISCONFIRMER_SEED: List[Dict] = [
    {
        "family": "5E",
        "transfer": True,
        "fields": {
            "SwappedCoverStory": "A reaction has dG = +12 kJ/mol at 298 K. Is it spontaneous as written?",
            "Answer": "No - it is nonspontaneous as written",
            "Principle": "Spontaneity is set by the sign of dG, not by dH alone.",
            "Trap": "Assuming an exothermic (or 'energy-releasing') reaction must be spontaneous.",
            "Disconfirmer": "If dG were negative - e.g. by coupling to ATP hydrolysis - the reaction would become spontaneous.",
            "BoundaryCase": "Because dG = dH - T dS, changing temperature can flip the sign.",
        },
    },
    {
        "family": "1D",
        "transfer": False,
        "fields": {
            "SwappedCoverStory": "A cell with no oxygen still nets 2 ATP from one glucose. Which pathway did it use?",
            "Answer": "Glycolysis (anaerobic)",
            "Principle": "Glycolysis is oxygen-independent and occurs in the cytoplasm.",
            "Trap": "Believing all ATP production requires oxygen.",
            "Disconfirmer": "If oxygen and functional mitochondria were present, oxidative phosphorylation would add far more ATP.",
            "BoundaryCase": "Mature red blood cells rely on glycolysis alone (no mitochondria).",
        },
    },
    {
        "family": "1A",
        "transfer": True,
        "fields": {
            "SwappedCoverStory": "At a pH well below a protein's isoelectric point (pI), what is its net charge?",
            "Answer": "Positive",
            "Principle": "Net charge depends on pH relative to the pI.",
            "Trap": "Assuming proteins are always negatively charged.",
            "Disconfirmer": "If the pH rose above the pI, the net charge would become negative.",
            "BoundaryCase": "At pH = pI the net charge is zero (the protein is least soluble).",
        },
    },
    {
        "family": "4C",
        "transfer": False,
        "fields": {
            "SwappedCoverStory": "Two identical resistors are wired in series. Is the total resistance higher or lower than one resistor?",
            "Answer": "Higher (it doubles)",
            "Principle": "Series resistances add; parallel resistances reduce the total.",
            "Trap": "Confusing the series and parallel combination rules.",
            "Disconfirmer": "If the two resistors were in parallel, the total would instead be half of one resistor.",
            "BoundaryCase": "The add-in-series / reduce-in-parallel pattern holds even for unequal resistors.",
        },
    },
    {
        "family": "6A",
        "transfer": True,
        "fields": {
            "SwappedCoverStory": "A dim light is detected 50% of the time at intensity X. What is X called?",
            "Answer": "The absolute threshold",
            "Principle": "Absolute threshold = the intensity detected 50% of the time.",
            "Trap": "Confusing it with the difference threshold.",
            "Disconfirmer": "If the question asked for the smallest detectable change between two stimuli, the answer would be the difference threshold (JND).",
            "BoundaryCase": "Thresholds shift with sensory adaptation and expectations.",
        },
    },
]


#: Pretest-first seed items (SPOV 13). Each is a forced first-exposure guess with
#: mandatory corrective feedback in ``explanation``. Answers are short so the native
#: type-in comparison is fair. Original ``[Sample]`` content; no copyrighted stems.
PRETEST_SEED: List[Dict] = [
    {
        "family": "1D",
        "question": "[Sample] A muscle runs out of oxygen mid-sprint but still makes a little ATP. Which pathway did it use?",
        "answer": "Glycolysis",
        "explanation": "Glycolysis runs in the cytoplasm without oxygen, netting 2 ATP per glucose. Oxygen only matters downstream at the electron transport chain.",
        "source": "[Sample] bioenergetics",
    },
    {
        "family": "1D",
        "question": "[Sample] What is the final electron acceptor of the electron transport chain?",
        "answer": "Oxygen",
        "explanation": "Oxygen accepts electrons at the end of the chain to form water; without it the chain backs up and oxidative ATP synthesis stalls.",
        "source": "[Sample] bioenergetics",
    },
    {
        "family": "5A",
        "question": "[Sample] You add a strong acid to pure water at 25C. Does the pH go above or below 7?",
        "answer": "Below",
        "explanation": "Adding H+ raises [H+], which lowers pH below the neutral value of 7 at 25C.",
        "source": "[Sample] acids and bases",
    },
    {
        "family": "4C",
        "question": "[Sample] Two equal resistors in series versus one alone: is total resistance higher or lower?",
        "answer": "Higher",
        "explanation": "Series resistances add, so two equal resistors double the total; in parallel the total would instead be halved.",
        "source": "[Sample] circuits",
    },
    {
        "family": "1A",
        "question": "[Sample] At a pH well below a protein's isoelectric point (pI), is its net charge positive or negative?",
        "answer": "Positive",
        "explanation": "Below the pI extra H+ protonates the protein for a net positive charge; above the pI it flips negative. At the pI the net charge is zero.",
        "source": "[Sample] amino acids",
    },
    {
        "family": "3B",
        "question": "[Sample] Which side of the heart pumps blood to the lungs?",
        "answer": "Right",
        "explanation": "The right side pumps deoxygenated blood to the lungs; the left side pumps oxygenated blood to the body.",
        "source": "[Sample] physiology",
    },
    {
        "family": "4A",
        "question": "[Sample] Net force doubles on the same mass. What happens to the acceleration?",
        "answer": "Doubles",
        "explanation": "F = ma, so at constant mass acceleration is proportional to force; doubling the force doubles the acceleration.",
        "source": "[Sample] mechanics",
    },
    {
        "family": "5D",
        "question": "[Sample] A carboxylic acid reacts with an alcohol. What functional group forms?",
        "answer": "Ester",
        "explanation": "Acid plus alcohol undergo condensation (losing water) to form an ester - the reverse of ester hydrolysis.",
        "source": "[Sample] organic chemistry",
    },
    {
        "family": "6A",
        "question": "[Sample] The dimmest light detectable 50% of the time defines which threshold?",
        "answer": "Absolute",
        "explanation": "The absolute threshold is the minimum intensity detected 50% of the time; the difference threshold is the smallest detectable change between two stimuli.",
        "source": "[Sample] sensation and perception",
    },
    {
        "family": "5E",
        "question": "[Sample] A reaction has a positive dH and a positive dS. Raising temperature makes dG more likely to be what sign?",
        "answer": "Negative",
        "explanation": "dG = dH - T*dS; a positive dS times a large T makes the -T*dS term dominate, driving dG negative (spontaneous) at high temperature.",
        "source": "[Sample] thermodynamics",
    },
]


def total_sample_cards() -> int:
    return sum(len(v) for v in SAMPLE_CARDS.values())
