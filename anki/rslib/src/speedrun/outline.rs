// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! The AAMC content outline, embedded as the ground-truth spine for the Speedrun
//! dashboard.
//!
//! This is the Rust port of `pylib/anki/speedrun/aamc_outline.py`: sections (each
//! with an abbreviation) and their content categories (`cc:<code>`, title). The
//! outline is structure only - no fabricated exam weights - and is *imported*,
//! never inferred, so it does not trip the "no auto-clustered concept clusters"
//! anti-pattern.
//!
//! Source: AAMC - "What's on the MCAT Exam?" content outline
//! <https://students-residents.aamc.org/whats-mcat-exam/whats-mcat-exam>
//!
//! The foundational-concept layer of the outline is intentionally flattened away
//! here: the dashboard rolls coverage/memory up from content category straight to
//! section, so the intermediate layer does not affect any value we return.

/// One MCAT content category (a leaf of the outline spine).
pub(crate) struct Category {
    /// The bare code, e.g. `1A` (the `cc:` id is `cc:1A`).
    pub code: &'static str,
    pub title: &'static str,
}

/// One MCAT section (e.g. Bio/Biochem), grouping its content categories.
pub(crate) struct Section {
    /// Stable outline id, e.g. `sec:bbls`.
    pub id: &'static str,
    /// Short label shown in the dashboard, e.g. `Bio/Biochem`.
    pub abbrev: &'static str,
    /// Official AAMC section title.
    pub title: &'static str,
    pub categories: &'static [Category],
}

/// The embedded outline, in AAMC order. CARS carries no content-category spine
/// (it requires no specific content knowledge), so it has no leaves and never
/// appears as a coverage row.
pub(crate) const SECTIONS: &[Section] = &[
    Section {
        id: "sec:bbls",
        abbrev: "Bio/Biochem",
        title: "Biological and Biochemical Foundations of Living Systems",
        categories: &[
            Category {
                code: "1A",
                title: "Structure and function of proteins and their constituent amino acids",
            },
            Category {
                code: "1B",
                title: "Transmission of genetic information from the gene to the protein",
            },
            Category {
                code: "1C",
                title: "Transmission of heritable information from generation to generation and the processes that increase genetic diversity",
            },
            Category {
                code: "1D",
                title: "Principles of bioenergetics and fuel molecule metabolism",
            },
            Category {
                code: "2A",
                title: "Assemblies of molecules, cells, and groups of cells within single cellular and multicellular organisms",
            },
            Category {
                code: "2B",
                title: "The structure, growth, physiology, and genetics of prokaryotes and viruses",
            },
            Category {
                code: "2C",
                title: "Processes of cell division, differentiation, and specialization",
            },
            Category {
                code: "3A",
                title: "Structure and functions of the nervous and endocrine systems and ways these systems coordinate the organ systems",
            },
            Category {
                code: "3B",
                title: "Structure and integrative functions of the main organ systems",
            },
        ],
    },
    Section {
        id: "sec:cpbs",
        abbrev: "Chem/Phys",
        title: "Chemical and Physical Foundations of Biological Systems",
        categories: &[
            Category {
                code: "4A",
                title: "Translational motion, forces, work, energy, and equilibrium in living systems",
            },
            Category {
                code: "4B",
                title: "Importance of fluids for the circulation of blood, gas movement, and gas exchange",
            },
            Category {
                code: "4C",
                title: "Electrochemistry and electrical circuits and their elements",
            },
            Category {
                code: "4D",
                title: "How light and sound interact with matter",
            },
            Category {
                code: "4E",
                title: "Atoms, nuclear decay, electronic structure, and atomic chemical behavior",
            },
            Category {
                code: "5A",
                title: "Unique nature of water and its solutions",
            },
            Category {
                code: "5B",
                title: "Nature of molecules and intermolecular interactions",
            },
            Category {
                code: "5C",
                title: "Separation and purification methods",
            },
            Category {
                code: "5D",
                title: "Structure, function, and reactivity of biologically relevant molecules",
            },
            Category {
                code: "5E",
                title: "Principles of chemical thermodynamics and kinetics",
            },
        ],
    },
    Section {
        id: "sec:psbb",
        abbrev: "Psych/Soc",
        title: "Psychological, Social, and Biological Foundations of Behavior",
        categories: &[
            Category {
                code: "6A",
                title: "Sensing the environment",
            },
            Category {
                code: "6B",
                title: "Making sense of the environment",
            },
            Category {
                code: "6C",
                title: "Responding to the world",
            },
            Category {
                code: "7A",
                title: "Individual influences on behavior",
            },
            Category {
                code: "7B",
                title: "Social processes that influence human behavior",
            },
            Category {
                code: "7C",
                title: "Attitude and behavior change",
            },
            Category {
                code: "8A",
                title: "Self-identity",
            },
            Category {
                code: "8B",
                title: "Social thinking",
            },
            Category {
                code: "8C",
                title: "Social interactions",
            },
            Category {
                code: "9A",
                title: "Understanding social structure",
            },
            Category {
                code: "9B",
                title: "Demographic characteristics and processes",
            },
            Category {
                code: "10A",
                title: "Social inequality",
            },
        ],
    },
    Section {
        id: "sec:cars",
        abbrev: "CARS",
        title: "Critical Analysis and Reasoning Skills",
        categories: &[],
    },
];

/// The `cc:` id for a bare content-category code (e.g. `1A` -> `cc:1A`).
pub(crate) fn cc_id(code: &str) -> String {
    format!("cc:{code}")
}

/// Whether `code` (e.g. `1A`) is a known content-category code.
pub(crate) fn is_known_code(code: &str) -> bool {
    SECTIONS
        .iter()
        .any(|s| s.categories.iter().any(|c| c.code == code))
}

/// The official title for a content-category code, if known.
pub(crate) fn title_for_code(code: &str) -> Option<&'static str> {
    SECTIONS
        .iter()
        .flat_map(|s| s.categories.iter())
        .find(|c| c.code == code)
        .map(|c| c.title)
}

/// Total number of content-category leaves across the whole outline.
pub(crate) fn total_leaves() -> u32 {
    SECTIONS.iter().map(|s| s.categories.len() as u32).sum()
}

/// Map a card tag to its content-category id (`cc:1A`), matching the last `::`
/// part that is a known content-category code.
///
/// Mirrors `_cc_from_tag` in the desktop dashboard: it walks the tag's `::`
/// parts from most-specific to least and returns the first that names a known
/// content category. For example `MCAT::BioBiochem::1A::AminoAcids` maps to
/// `cc:1A`. Returns `None` when no part names a content category.
pub(crate) fn cc_from_tag(tag: &str) -> Option<String> {
    // `rsplit` walks the `::` parts from most-specific to least (right to left),
    // matching the Python's `reversed(tag.split("::"))`.
    tag.rsplit("::")
        .map(str::trim)
        .find(|part| is_known_code(part))
        .map(cc_id)
}
