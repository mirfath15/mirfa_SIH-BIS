import glob
import os
import re
from dataclasses import dataclass, field
from typing import List

import streamlit as st

import config

# ---------------------------------------------------------------------------
# 1. KNOWLEDGE BASE (curated seed chunks, clause-by-clause)
#
# This curated list works as an offline "gold" knowledge base so the app
# runs correctly out of the box with zero setup. It is combined with any
# real BIS PDFs found in data/raw_pdfs/ (see the ingestion functions below)
# and both are embedded into the same ChromaDB collection.
# ---------------------------------------------------------------------------


@dataclass
class Chunk:
    """A single retrievable clause-level knowledge chunk."""

    chunk_id: str
    service: str
    standard: str
    clause: str
    title: str
    text: str
    source: str
    keywords: List[str] = field(default_factory=list)


KNOWLEDGE_BASE: List[Chunk] = [
    # ---------------- Hallmarking (Gold/Silver Jewellery) ----------------
    Chunk(
        chunk_id="HM-001",
        service="Hallmarking",
        standard="IS 1417 : 2016 (Hallmarking of Gold Jewellery/Artefacts)",
        clause="Clause 4.2",
        title="Mandatory Hallmarking of Gold Jewellery",
        text=(
            "Gold jewellery and artefacts sold in India must carry a BIS "
            "hallmark consisting of the BIS Standard Mark, purity/fineness "
            "grade (e.g. 22K916, 18K750), and a 6-digit alphanumeric HUID "
            "(Hallmark Unique Identification) number. Jewellers must be "
            "registered with BIS and get each piece hallmarked at a "
            "BIS-recognised Assaying & Hallmarking Centre (AHC)."
        ),
        source="BIS Hallmarking Scheme, IS 1417:2016, Clause 4.2",
        keywords=[
            "hallmark",
            "gold",
            "jewellery",
            "jewelry",
            "purity",
            "huid",
            "22k",
            "18k",
            "gold jewellery",
            "hallmarking",
            "mandatory hallmarking of gold jewellery",
        ],
    ),
    Chunk(
        chunk_id="HM-002",
        service="Hallmarking",
        standard="IS 2790 : 2020 (Hallmarking of Silver Jewellery/Artefacts)",
        clause="Clause 5.1",
        title="Silver Jewellery Hallmarking Grades",
        text=(
            "Silver jewellery/artefacts are hallmarked under six grades of "
            "fineness: 990, 970, 925 (Sterling Silver), 900, 835, and 800. "
            "Each hallmark must carry the BIS mark, the fineness grade, and "
            "the jeweller's registration number issued by BIS."
        ),
        source="BIS Hallmarking Scheme, IS 2790:2020, Clause 5.1",
        keywords=[
            "silver",
            "sterling",
            "925",
            "silver jewellery",
            "silver hallmark",
            "fineness",
            "clause 5.1",
        ],
    ),
    # ---------------- Product Certification / ISI Mark (Toy & Helmet) ----
    Chunk(
        chunk_id="TOY-001",
        service="Product Certification (ISI Mark)",
        standard="IS 9873 (Part 1) : 2019 (Safety of Toys)",
        clause="Clause 6.3",
        title="Mandatory ISI Certification for Toys",
        text=(
            "All toys intended for children below 14 years, manufactured, "
            "imported, or sold in India, must comply with IS 9873 (Part 1) "
            "for mechanical & physical safety and bear the ISI mark under "
            "the BIS Compulsory Registration Scheme. Manufacturers must "
            "obtain a valid BIS licence before selling toys in the market."
        ),
        source="BIS Toy Safety Order, IS 9873(Part 1):2019, Clause 6.3",
        keywords=[
            "toy",
            "toys",
            "isi",
            "children",
            "toy safety",
            "toy license",
            "toy licence",
            "toy certification",
            "clause 6.3",
        ],
    ),
    Chunk(
        chunk_id="HEL-001",
        service="Product Certification (ISI Mark)",
        standard="IS 4151 : 2015 (Protective Helmets for Two-Wheeler Riders)",
        clause="Clause 7.2",
        title="Mandatory ISI Mark on Helmets",
        text=(
            "Protective helmets for two-wheeler riders must conform to IS "
            "4151:2015 and carry the ISI mark. Sale, manufacture or import "
            "of helmets without a valid BIS licence and ISI mark is "
            "prohibited under the Helmets (Quality Control) Order, 2020."
        ),
        source="Helmets (Quality Control) Order 2020 / IS 4151:2015, Clause 7.2",
        keywords=[
            "helmet",
            "helmets",
            "two wheeler",
            "isi helmet",
            "helmet license",
            "helmet licence",
            "bike helmet",
            "clause 7.2",
        ],
    ),
    # ---------------- Electronics and IT Equipment Rules ----------------
    Chunk(
        chunk_id="ELEC-001",
        service="Product Certification (CRS)",
        standard="IS 13252 (Part 1) : 2010 (Information Technology Equipment)",
        clause="IS 13252 (Part 1)",
        title="High-Voltage Insulation Tests for Laptops and IT Equipment",
        text=(
            "Laptops and IT equipment must pass strict high-voltage insulation "
            "tests to prevent electrical shocks to users."
        ),
        source="IS 13252 (Part 1)",
        keywords=["laptops", "it equipment", "is 13252", "high-voltage insulation", "electric shock", "electronics"],
    ),
    Chunk(
        chunk_id="ELEC-002",
        service="Product Certification (CRS)",
        standard="IS 16333 (Part 3) : 2022 (Indian Language Support for Mobile Phones)",
        clause="IS 16333 (Part 3)",
        title="Indian Language Support Requirements for Mobile Phones",
        text=(
            "Mobile phones sold in India must display and support text input for "
            "at least 22 official Indian languages."
        ),
        source="IS 16333 (Part 3)",
        keywords=["mobile phones", "smartphones", "is 16333", "indian languages", "text input", "multilingual"],
    ),
    Chunk(
        chunk_id="ELEC-003",
        service="Product Certification (ISI Mark)",
        standard="IS 302 (Part 1) : 2024 (Safety of Household Appliances)",
        clause="IS 302 (Part 1)",
        title="Effective Earthing Mechanism for Domestic Appliances",
        text=(
            "Domestic appliances must feature an effective earthing mechanism to safely route stray currents."
        ),
        source="IS 302 (Part 1)",
        keywords=["domestic appliances", "is 302", "earthing", "stray currents", "household safety"],
    ),
    Chunk(
        chunk_id="ELEC-004",
        service="Product Certification (ISI Mark)",
        standard="IS 302 (Part 2/Sec 3) : Electric Irons",
        clause="IS 302 (Part 2/Sec 3)",
        title="Functional Thermostat for Electric Irons",
        text=(
            "Electric irons must include a functional thermostat that automatically cuts power to prevent overheating and fire."
        ),
        source="IS 302 (Part 2/Sec 3)",
        keywords=["electric irons", "thermostat", "overheating", "fire prevention", "is 302"],
    ),
    Chunk(
        chunk_id="ELEC-005",
        service="Product Certification (ISI Mark)",
        standard="IS 302 (Part 2/Sec 201) : Immersion Heaters",
        clause="IS 302 (Part 2/Sec 201)",
        title="Leak-Proof Structure for Immersion Heaters",
        text=(
            "Immersion heaters must be structurally leak-proof to prevent current leakage into the water during use."
        ),
        source="IS 302 (Part 2/Sec 201)",
        keywords=["immersion heaters", "leak-proof", "current leakage", "water heater", "is 302"],
    ),
    Chunk(
        chunk_id="ELEC-006",
        service="Product Certification (ISI Mark)",
        standard="IS 302 (Part 2/Sec 26) : Microwave Ovens",
        clause="IS 302 (Part 2/Sec 26)",
        title="Radiation Leakage Limits for Microwave Ovens",
        text=(
            "Microwave ovens must maintain radiation leakage levels strictly below 50 Watts per square meter."
        ),
        source="IS 302 (Part 2/Sec 26)",
        keywords=["microwave ovens", "radiation leakage", "is 302", "radiation limits"],
    ),
    Chunk(
        chunk_id="ELEC-007",
        service="Product Certification (ISI Mark)",
        standard="IS 616 : Audio, Video and Similar Electronic Apparatus",
        clause="IS 616",
        title="Structural Stability and Flame-Retardance of AV Devices",
        text=(
            "Audio and video devices must remain structurally stable and flame-retardant under extreme high-temperature operation."
        ),
        source="IS 616",
        keywords=["audio devices", "video devices", "is 616", "flame-retardant", "high-temperature"],
    ),
    Chunk(
        chunk_id="ELEC-008",
        service="Product Certification (ISI Mark)",
        standard="IS 14218 : Power Adapters",
        clause="IS 14218",
        title="Input Over-Voltage Protection for Power Adapters",
        text=(
            "Power adapters must prevent input over-voltages from passing through and damaging connected electronic devices."
        ),
        source="IS 14218",
        keywords=["power adapters", "chargers", "over-voltage", "is 14218", "electronic protection"],
    ),
    Chunk(
        chunk_id="ELEC-009",
        service="Product Certification (CRS)",
        standard="IS 16046 (Part 1) : Secondary Cells Containing Alkaline or Other Non-Acid Electrolytes",
        clause="IS 16046 (Part 1)",
        title="Safety of Sealed Industrial Nickel Batteries",
        text=(
            "Sealed industrial nickel batteries must not explode or catch fire during an accidental external short circuit."
        ),
        source="IS 16046 (Part 1)",
        keywords=["nickel batteries", "industrial batteries", "is 16046", "short circuit", "battery safety"],
    ),
    Chunk(
        chunk_id="ELEC-010",
        service="Product Certification (CRS)",
        standard="IS 16046 (Part 2) : Secondary Cells Containing Alkaline or Other Non-Acid Electrolytes",
        clause="IS 16046 (Part 2)",
        title="Drop and Crush Testing for Portable Lithium-Ion Batteries",
        text=(
            "Portable lithium-ion mobile batteries must pass rigorous drop tests and crushing forces without venting or leaking."
        ),
        source="IS 16046 (Part 2)",
        keywords=["lithium-ion", "mobile batteries", "is 16046", "drop test", "crushing test", "battery leak"],
    ),

    # ---------------- Automotive Rules ----------------
    Chunk(
        chunk_id="AUTO-001",
        service="Automotive Certification",
        standard="IS 15633 : Automotive Tyres for Passenger Cars",
        clause="IS 15633",
        title="Durability and Speed Performance for Passenger Car Tyres",
        text=(
            "Passenger car tires must sustain maximum rated speeds and heavy loads without tread separation or structural cracking."
        ),
        source="IS 15633",
        keywords=["passenger car tires", "tyres", "is 15633", "tread separation", "speed performance"],
    ),
    Chunk(
        chunk_id="AUTO-002",
        service="Automotive Certification",
        standard="IS 15636 : Automotive Wheel Rims",
        clause="IS 15636",
        title="Rotational Bending Fatigue Testing for Vehicle Wheel Rims",
        text=(
            "Vehicle wheel rims must pass rotational bending fatigue tests to ensure they do not crack under sharp turns."
        ),
        source="IS 15636",
        keywords=["wheel rims", "is 15636", "fatigue test", "turns", "automotive parts"],
    ),
    Chunk(
        chunk_id="AUTO-003",
        service="Automotive Certification",
        standard="IS 15627 : Two-Wheeler Pneumatic Tyres",
        clause="IS 15627",
        title="Tread Wear Indicator Depth for Two-Wheeler Tyres",
        text=(
            "Two-wheeler pneumatic tires must have a minimum tread wear indicator depth to ensure safe road grip."
        ),
        source="IS 15627",
        keywords=["two-wheeler tires", "pneumatic tyres", "is 15627", "tread depth", "road grip"],
    ),
    Chunk(
        chunk_id="AUTO-004",
        service="Automotive Certification",
        standard="IS 2796 : Commercial Petrol (Automotive Fuels)",
        clause="IS 2796",
        title="Octane Rating and Benzene Limits for Commercial Petrol",
        text=(
            "Commercial petrol must maintain a specific octane rating and limit benzene content to curb toxic emissions."
        ),
        source="IS 2796",
        keywords=["petrol", "automotive fuel", "is 2796", "octane rating", "benzene limit", "emissions"],
    ),
    Chunk(
        chunk_id="AUTO-005",
        service="Automotive Certification",
        standard="IS 1460 : Automotive Diesel Fuel",
        clause="IS 1460",
        title="Sulfur Content Limits for Automotive Diesel",
        text=(
            "Automotive diesel must limit total sulfur content to prevent rapid engine corrosion and heavy air pollution."
        ),
        source="IS 1460",
        keywords=["diesel", "automotive diesel", "is 1460", "sulfur content", "engine corrosion"],
    ),
    Chunk(
        chunk_id="AUTO-006",
        service="Automotive Certification",
        standard="IS 13015 : Interior Rear-View Mirrors",
        clause="IS 13015",
        title="Shatterproof Glass Standards for Interior Rear-View Mirrors",
        text=(
            "Interior rear-view mirrors must use shatterproof glass that does not produce sharp shards upon sudden impact."
        ),
        source="IS 13015",
        keywords=["rear-view mirrors", "shatterproof glass", "is 13015", "mirror safety"],
    ),
    Chunk(
        chunk_id="AUTO-007",
        service="Automotive Certification",
        standard="IS 2190 : Selection, Installation and Maintenance of Fire Extinguishers",
        clause="IS 2190",
        title="Fire Extinguishers for Commercial Transport Vehicles",
        text=(
            "Commercial transport vehicles must carry easily accessible fire extinguishers rated for both chemical and electrical fires."
        ),
        source="IS 2190",
        keywords=["fire extinguishers", "transport vehicles", "is 2190", "vehicle safety", "electrical fires"],
    ),
    Chunk(
        chunk_id="AUTO-008",
        service="Automotive Certification",
        standard="IS 1598 : Steel for Critical Automotive Applications",
        clause="IS 1598",
        title="Impact Energy Absorption for Critical Steel Auto Parts",
        text=(
            "Critical steel auto parts must absorb specified impact energy levels without suffering immediate brittle fractures."
        ),
        source="IS 1598",
        keywords=["steel auto parts", "is 1598", "impact energy", "brittle fracture", "automotive steel"],
    ),

    # ---------------- Construction Rules ----------------
    Chunk(
        chunk_id="CONST-001",
        service="Construction Materials Certification",
        standard="IS 456 : Plain and Reinforced Concrete",
        clause="IS 456",
        title="Cement Content and Water-Cement Ratios in Concrete",
        text=(
            "Reinforced concrete designs must maintain minimum cement content and specific water-cement ratios to guarantee structural longevity."
        ),
        source="IS 456",
        keywords=["reinforced concrete", "is 456", "water-cement ratio", "cement content", "structural longevity"],
    ),
    Chunk(
        chunk_id="CONST-002",
        service="Construction Materials Certification",
        standard="IS 1786 : High Strength Deformed Steel Bars and Wires for Concrete Reinforcement",
        clause="IS 1786",
        title="Minimum Elongation Percentage for TMT Steel Bars",
        text=(
            "TMT steel bars must achieve a minimum elongation percentage of 14.5% to ensure buildings can withstand earthquakes."
        ),
        source="IS 1786",
        keywords=["tmt steel bars", "is 1786", "elongation percentage", "earthquake resistance", "reinforcement"],
    ),
    Chunk(
        chunk_id="CONST-003",
        service="Construction Materials Certification",
        standard="IS 269 : Ordinary Portland Cement (53 Grade)",
        clause="IS 269",
        title="Compressive Strength Standard for OPC 53 Cement",
        text=(
            "Ordinary Portland Cement (OPC 53) must achieve a minimum compressive strength of 53 Megapascals after 28 days of setting."
        ),
        source="IS 269",
        keywords=["ordinary portland cement", "opc 53", "is 269", "compressive strength", "cement"],
    ),
    Chunk(
        chunk_id="CONST-004",
        service="Construction Materials Certification",
        standard="IS 1489 (Part 1) : Portland Pozzolana Cement",
        clause="IS 1489 (Part 1)",
        title="Fly Ash Content Limits in Portland Pozzolana Cement",
        text=(
            "Portland Pozzolana Cement must strictly limit fly ash content between 15% and 35% to maintain structural strength."
        ),
        source="IS 1489 (Part 1)",
        keywords=["portland pozzolana cement", "ppc", "is 1489", "fly ash content"],
    ),
    Chunk(
        chunk_id="CONST-005",
        service="Construction Materials Certification",
        standard="IS 383 : Coarse and Fine Aggregates for Concrete",
        clause="IS 383",
        title="Purity Standards for Fine Aggregates (Sand) in Concrete",
        text=(
            "Fine aggregates (sand) used in concrete mixes must be entirely free of clay, silt, and organic impurities."
        ),
        source="IS 383",
        keywords=["fine aggregates", "sand", "is 383", "concrete mix", "impurities"],
    ),
    Chunk(
        chunk_id="CONST-006",
        service="Construction Materials Certification",
        standard="IS 800 : General Construction in Steel",
        clause="IS 800",
        title="Weld Sizes and Bolt Tensions for Structural Steel Connections",
        text=(
            "Structural steel connections must be designed using specific weld sizes and bolt tensions to prevent structural collapse."
        ),
        source="IS 800",
        keywords=["structural steel", "is 800", "steel connections", "weld size", "bolt tension"],
    ),
    Chunk(
        chunk_id="CONST-007",
        service="Construction Materials Certification",
        standard="IS 4984 : High Density Polyethylene Pipes for Water Supply",
        clause="IS 4984",
        title="Hydrostatic Pressure Resistance for HDPE Water Pipes",
        text=(
            "High-Density Polyethylene water pipes must withstand continuous internal hydrostatic pressure tests without bursting."
        ),
        source="IS 4984",
        keywords=["hdpe pipes", "polyethylene pipes", "is 4984", "hydrostatic pressure", "water pipes"],
    ),
    Chunk(
        chunk_id="CONST-008",
        service="Construction Materials Certification",
        standard="IS 1239 (Part 1) : Mild Steel Tubes and Tubulars",
        clause="IS 1239 (Part 1)",
        title="Non-Destructive Eddy Current Testing for Mild Steel Plumbing Tubes",
        text=(
            "Mild steel tubes used for plumbing must undergo non-destructive eddy current testing to eliminate weld defects."
        ),
        source="IS 1239 (Part 1)",
        keywords=["mild steel tubes", "is 1239", "plumbing pipes", "eddy current testing", "weld defects"],
    ),
    Chunk(
        chunk_id="CONST-009",
        service="Construction Materials Certification",
        standard="IS 875 (Part 3) : Design Loads for Buildings and Structures (Wind Loads)",
        clause="IS 875 (Part 3)",
        title="Regional Peak Wind Speed Engineering for Buildings",
        text=(
            "Buildings must be engineered to resist regional peak wind speeds, calculated using specific terrain and height factors."
        ),
        source="IS 875 (Part 3)",
        keywords=["wind loads", "is 875", "peak wind speed", "building design", "terrain factors"],
    ),

    # ---------------- Food and Agriculture Rules ----------------
    Chunk(
        chunk_id="AGRI-001",
        service="Food and Drinks Certification",
        standard="IS 14543 : Packaged Drinking Water",
        clause="IS 14543",
        title="Microbiological Safety Standards for Packaged Drinking Water",
        text=(
            "Packaged drinking water must strictly show zero counts of E. coli and Coliform bacteria in any 250ml sample."
        ),
        source="IS 14543",
        keywords=["packaged drinking water", "is 14543", "e. coli", "coliform", "microbiological safety"],
    ),
    Chunk(
        chunk_id="AGRI-002",
        service="Food and Drinks Certification",
        standard="IS 13428 : Packaged Natural Mineral Water",
        clause="IS 13428",
        title="Source Bottling Requirements for Natural Mineral Water",
        text=(
            "Packaged natural mineral water must be bottled directly at the natural source without altering its original mineral composition."
        ),
        source="IS 13428",
        keywords=["natural mineral water", "is 13428", "mineral composition", "source bottling"],
    ),
    Chunk(
        chunk_id="AGRI-003",
        service="Food and Drinks Certification",
        standard="IS 1165 : Milk Powder",
        clause="IS 1165",
        title="Moisture Content Limits for Commercial Milk Powder",
        text=(
            "Commercial milk powder must limit total moisture content to a maximum of 4% to prevent premature bacterial spoilage."
        ),
        source="IS 1165",
        keywords=["milk powder", "is 1165", "moisture content", "bacterial spoilage"],
    ),
    Chunk(
        chunk_id="AGRI-004",
        service="Food and Drinks Certification",
        standard="IS 14433 : Infant Milk Substitutes",
        clause="IS 14433",
        title="Additive Restrictions for Infant Milk Formulas",
        text=(
            "Infant milk formulas must be entirely free from starch, added artificial colors, and commercial chemical preservatives."
        ),
        source="IS 14433",
        keywords=["infant milk formulas", "is 14433", "baby milk", "no starch", "artificial colors"],
    ),
    Chunk(
        chunk_id="AGRI-005",
        service="Food and Drinks Certification",
        standard="IS 1166 : Condensed Milk",
        clause="IS 1166",
        title="Minimum Milk Solid Content for Condensed Milk",
        text=(
            "Condensed milk must maintain a minimum total milk solid content of 26% to ensure proper nutritional value."
        ),
        source="IS 1166",
        keywords=["condensed milk", "is 1166", "milk solid content", "nutritional value"],
    ),
    Chunk(
        chunk_id="AGRI-006",
        service="Food and Drinks Certification",
        standard="IS 4905 : Methods for Random Sampling",
        clause="IS 4905",
        title="Unbiased Random Number Tables for Food Batch Sampling",
        text=(
            "Food batch sampling must utilize unbiased random number tables to ensure fair and accurate quality assessments."
        ),
        source="IS 4905",
        keywords=["food batch sampling", "is 4905", "random sampling", "quality assessment"],
    ),
    Chunk(
        chunk_id="AGRI-007",
        service="Food and Drinks Certification",
        standard="IS 7654 : Grain Storage Silos",
        clause="IS 7654",
        title="Functional Aeration Ducts for Grain Storage Silos",
        text=(
            "Grain storage silos must incorporate functional aeration ducts to prevent moisture buildup and mold growth."
        ),
        source="IS 7654",
        keywords=["grain storage silos", "is 7654", "aeration ducts", "mold prevention"],
    ),
    Chunk(
        chunk_id="AGRI-008",
        service="Food and Drinks Certification",
        standard="IS 15000 : Food Safety Management Systems (HACCP)",
        clause="IS 15000",
        title="Critical Control Points Identification in Food Processing",
        text=(
            "Food processing facilities must identify critical control points to permanently eliminate physical and chemical food hazards."
        ),
        source="IS 15000",
        keywords=["food processing facilities", "is 15000", "haccp", "critical control points", "food hazards"],
    ),

    # ---------------- Chemicals and Polymers Rules ----------------
    Chunk(
        chunk_id="CHEM-001",
        service="Chemicals Certification",
        standard="IS 266 : Sulphuric Acid",
        clause="IS 266",
        title="Impurity Limits for Industrial Sulphuric Acid",
        text=(
            "Industrial sulphuric acid must strictly limit arsenic and iron impurities to avoid dangerous chemical side-reactions."
        ),
        source="IS 266",
        keywords=["sulphuric acid", "is 266", "acid impurities", "arsenic limit", "industrial chemical"],
    ),
    Chunk(
        chunk_id="CHEM-002",
        service="Chemicals Certification",
        standard="IS 296 : Sodium Carbonate (Soda Ash)",
        clause="IS 296",
        title="Purity Level Standard for Industrial Soda Ash",
        text=(
            "Industrial soda ash must maintain a minimum sodium carbonate purity level of 98.5% by total weight."
        ),
        source="IS 296",
        keywords=["soda ash", "sodium carbonate", "is 296", "purity level"],
    ),
    Chunk(
        chunk_id="CHEM-003",
        service="Chemicals Certification",
        standard="IS 695 : Glacial Acetic Acid",
        clause="IS 695",
        title="Solidification Point Testing for Glacial Acetic Acid",
        text=(
            "Glacial acetic acid must solidify precisely at 16.2 degrees Celsius to prove its chemical purity and concentration."
        ),
        source="IS 695",
        keywords=["glacial acetic acid", "is 695", "solidification point", "chemical purity"],
    ),
    Chunk(
        chunk_id="CHEM-004",
        service="Chemicals Certification",
        standard="IS 170 : Acetone (Technical Grade)",
        clause="IS 170",
        title="Residue and Evaporation Standards for Technical Acetone",
        text=(
            "Technical-grade acetone solvents must leave absolutely no oily residue or visible stain after complete evaporation."
        ),
        source="IS 170",
        keywords=["acetone", "technical grade", "is 170", "solvent evaporation", "residue free"],
    ),
    Chunk(
        chunk_id="CHEM-005",
        service="Chemicals Certification",
        standard="IS 1070 : Reagent Water for Laboratory Use",
        clause="IS 1070",
        title="Electrical Conductivity Limits for Laboratory Reagent Water",
        text=(
            "Laboratory reagent water must maintain an electrical conductivity below 0.1 milli-Siemens per meter to prevent testing errors."
        ),
        source="IS 1070",
        keywords=["reagent water", "laboratory water", "is 1070", "electrical conductivity"],
    ),
    Chunk(
        chunk_id="CHEM-006",
        service="Chemicals Certification",
        standard="IS 10116 : Polyvinyl Chloride (PVC) Resins",
        clause="IS 10116",
        title="Residual Vinyl Chloride Monomer Limits in PVC Resins",
        text=(
            "Raw Polyvinyl Chloride (PVC) resins must strictly limit residual vinyl chloride monomer to under 5 parts per million."
        ),
        source="IS 10116",
        keywords=["pvc resins", "polyvinyl chloride", "is 10116", "vinyl chloride monomer"],
    ),
    Chunk(
        chunk_id="CHEM-007",
        service="Chemicals Certification",
        standard="IS 9833 : Plastics for Food Contact Applications",
        clause="IS 9833",
        title="Heavy Metal Exclusions in Food-Contact Plastics",
        text=(
            "Plastics contacting food items must strictly exclude toxic heavy metals like lead, cadmium, and mercury from colorants."
        ),
        source="IS 9833",
        keywords=["food contact plastics", "is 9833", "heavy metals", "lead-free", "cadmium-free"],
    ),
    Chunk(
        chunk_id="CHEM-008",
        service="Chemicals Certification",
        standard="IS 533 : Gum Spirit of Turpentine",
        clause="IS 533",
        title="Absence of Mineral Oils in Gum Spirit of Turpentine",
        text=(
            "Gum spirit of turpentine must remain completely free of mineral oils and unpolymerized petroleum residues."
        ),
        source="IS 533",
        keywords=["turpentine", "gum spirit", "is 533", "no mineral oils"],
    ),

    # ---------------- Toys and Consumer Goods Rules ----------------
    Chunk(
        chunk_id="TOY-002",
        service="Product Certification (ISI Mark)",
        standard="IS 9873 (Part 1) : Safety of Toys - Mechanical and Physical Properties",
        clause="IS 9873 (Part 1)",
        title="Mechanical Safety Requirements for Children's Toys",
        text=(
            "Children's toys must not have any sharp edges, hazardous points, or small parts that pose choking risks."
        ),
        source="IS 9873 (Part 1)",
        keywords=["toys", "is 9873 part 1", "sharp edges", "choking risk", "mechanical safety"],
    ),
    Chunk(
        chunk_id="TOY-003",
        service="Product Certification (ISI Mark)",
        standard="IS 9873 (Part 2) : Safety of Toys - Flammability",
        clause="IS 9873 (Part 2)",
        title="Flammability Resistance Limits for Toy Materials",
        text=(
            "Toy materials must not catch fire instantly or propagate flames faster than 30 millimeters per second."
        ),
        source="IS 9873 (Part 2)",
        keywords=["toys flammability", "is 9873 part 2", "fire resistance", "flame propagation"],
    ),
    Chunk(
        chunk_id="TOY-004",
        service="Product Certification (ISI Mark)",
        standard="IS 9873 (Part 3) : Safety of Toys - Migration of Certain Elements",
        clause="IS 9873 (Part 3)",
        title="Soluble Lead Migration Limits in Toy Coatings",
        text=(
            "Soluble lead migration from toy coatings is strictly capped at a maximum of 90 milligrams per kilogram."
        ),
        source="IS 9873 (Part 3)",
        keywords=["toy coatings", "is 9873 part 3", "soluble lead", "migration limit"],
    ),
    Chunk(
        chunk_id="TOY-005",
        service="Product Certification (ISI Mark)",
        standard="IS 9873 (Part 4) : Swings, Slides and Similar Activity Toys",
        clause="IS 9873 (Part 4)",
        title="Anchoring Requirements for Playground Activity Swings and Slides",
        text=(
            "Activity swings and slides must include anchor points that prevent tipping over under maximum child weight loads."
        ),
        source="IS 9873 (Part 4)",
        keywords=["swings", "slides", "is 9873 part 4", "activity toys", "anchor points"],
    ),
    Chunk(
        chunk_id="TOY-006",
        service="Product Certification (ISI Mark)",
        standard="IS 9873 (Part 9) : Safety of Toys - Phthalates in Toys",
        clause="IS 9873 (Part 9)",
        title="Phthalate Restrictions in Plastic Toys",
        text=(
            "Plastic toys must strictly exclude hazardous phthalate plasticizers to safeguard children from hormonal toxins."
        ),
        source="IS 9873 (Part 9)",
        keywords=["plastic toys", "is 9873 part 9", "phthalates", "hormonal toxins"],
    ),
    Chunk(
        chunk_id="TOY-007",
        service="Product Certification (ISI Mark)",
        standard="IS 15644 : Safety of Electric Toys",
        clause="IS 15644",
        title="Maximum Voltage Restrictions for Electrical Toy Mechanisms",
        text=(
            "Electrical toy mechanisms must restrict their operating voltage to a maximum of 24 Volts to prevent shocks."
        ),
        source="IS 15644",
        keywords=["electric toys", "is 15644", "voltage limit", "24 volts", "toy safety"],
    ),
    Chunk(
        chunk_id="TOY-008",
        service="Product Certification (ISI Mark)",
        standard="IS 694 : Polyvinyl Chloride Insulated Cables",
        clause="IS 694",
        title="Copper Purity Standard for Domestic PVC Insulated Cables",
        text=(
            "Domestic PVC insulated cables must use 99.9% pure electrolytic copper to prevent overheating in household wiring."
        ),
        source="IS 694",
        keywords=["pvc cables", "is 694", "electrolytic copper", "household wiring", "insulated cables"],
    ),

    # ---------------- Food and Drinks (BIS Standards) ----------------
    Chunk(
        chunk_id="FOOD-001",
        service="Food and Drinks Certification",
        standard="IS 14543 : 2016 (Packaged Drinking Water)",
        clause="Clause 4.1",
        title="Mandatory ISI Mark for Packaged Drinking Water & Drinks",
        text=(
            "Packaged drinking water, carbonated beverages, and liquid drinks "
            "processed and sold in bottles or containers must strictly comply "
            "with relevant standards under Section 16 of the BIS Act, 2016[cite: 1]. "
            "It is mandatory for manufacturers to obtain a BIS product certification "
            "licence and display the ISI mark before commercial distribution[cite: 1]."
        ),
        source="BIS Act 2016 Section 16 / IS 14543:2016, Clause 4.1[cite: 1]",
        keywords=[
            "water",
            "packaged drinking water",
            "bottle water",
            "drinks",
            "beverages",
            "is 14543",
            "drinking water standard",
            "water bottle license",
            "clause 4.1",
        ],
    ),
    Chunk(
        chunk_id="FOOD-002",
        service="Food and Drinks Certification",
        standard="IS 13428 : 2005 (Packaged Natural Mineral Water)",
        clause="Clause 5.3",
        title="Source Requirements for Natural Mineral Water",
        text=(
            "Packaged natural mineral water must be obtained directly from "
            "natural underground or subterranean water sources protected "
            "from pollution risks. The water must be bottled at the source "
            "under hygienic conditions without any chemical treatments "
            "other than permitted physical separation techniques, conforming "
            "to IS 13428."
        ),
        source="BIS Standard IS 13428:2005, Clause 5.3",
        keywords=[
            "mineral water",
            "natural water",
            "is 13428",
            "underground water",
            "spring water",
            "clause 5.3",
        ],
    ),
    Chunk(
        chunk_id="FOOD-003",
        service="Food and Drinks Certification",
        standard="IS 13688 : 1992 (Packaged Pasteurized Milk)",
        clause="Clause 3.2",
        title="Quality, Safety, and Packaging Parameters for Pasteurized Milk",
        text=(
            "Dairy processing units supplying packaged pasteurized milk "
            "must comply with BIS quality control parameters regarding "
            "fat content, solids-not-fat (SNF), and microbial safety limits[cite: 1]. "
            "Under Section 18 of the BIS Act, 2016, milk sellers must ensure "
            "packets bear requisite labeling, freshness details, and expiration parameters[cite: 1]."
        ),
        source="BIS Act 2016 Section 18 / IS 13688:1992, Clause 3.2[cite: 1]",
        keywords=[
            "milk",
            "pasteurized milk",
            "dairy",
            "packaged milk",
            "fat content",
            "snf",
            "milk license",
            "expiration",
            "clause 3.2",
        ],
    ),
    Chunk(
        chunk_id="FOOD-004",
        service="Food and Drinks Certification",
        standard="BIS Act, 2016 - Packaged Foods & Snacks (Chips)",
        clause="Section 16 & 18",
        title="Compulsory Certification and Expiration Rules for Packaged Snacks (Chips)",
        text=(
            "Packaged snack items such as chips and crisps fall under goods and articles "
            "notified under Section 16 of the BIS Act, 2016, requiring compulsory standard marks[cite: 1]. "
            "Product specifications under Section 2(37) include shelf-life, durability, and expiration dates[cite: 1]. "
            "Sellers and distributors must verify proper labeling and ensure items are sourced from certified licensees[cite: 1]."
        ),
        source="BIS Act, 2016, Sections 16, 18 & 2(37)[cite: 1]",
        keywords=[
            "chips",
            "snacks",
            "packaged food",
            "expiration",
            "shelf life",
            "expiry",
            "food safety",
            "labeling",
            "section 16 & 18",
        ],
    ),
    # ---------------- Statutory Sections & Legal Framework ----------------
    Chunk(
        chunk_id="SEC-16",
        service="Compulsory Certification",
        standard="BIS Act, 2016 - Section 16",
        clause="Compulsory Certification Provisions (Section 16)",
        title="Central Government Power & Compulsory Notification Grounds",
        text=(
            "If the Central Government deems it necessary or expedient in the public interest, "
            "it may issue an order in the Official Gazette to mandate compulsory certification[cite: 1]. "
            "Grounds include protection of human, animal, or plant health, environmental safety, "
            "prevention of unfair trade practices, or national security[cite: 1]. "
            "The government may notify goods of any scheduled industry (under Industries IDR Act 1951) "
            "along with essential requirements, authorizing the Bureau or accredited agencies to enforce conformity[cite: 1]."
        ),
        source="BIS Act, 2016, Section 16[cite: 1]",
        keywords=[
            "section 16",
            "central government power",
            "compulsory certification provisions",
            "scheduled industries",
            "essential requirements",
            "public interest",
        ],
    ),
    Chunk(
        chunk_id="SEC-17",
        service="Licensing and Enforcement",
        standard="BIS Act, 2016 - Section 17",
        clause="Prohibitions and Restrictions (Section 17)",
        title="Manufacture, Sale, False Claims, and Imitation Restrictions",
        text=(
            "No person is permitted to manufacture, import, distribute, sell, store, or exhibit for sale "
            "any goods or services notified under compulsory certification without a valid licence or Standard Mark[cite: 1]. "
            "Making false public claims via advertisements or price lists declaring conformity without a valid certificate is prohibited[cite: 1]. "
            "Using a Standard Mark or any colourable imitation thereof without a valid licence is strictly restricted[cite: 1]."
        ),
        source="BIS Act, 2016, Section 17[cite: 1]",
        keywords=[
            "section 17",
            "prohibitions and restrictions",
            "manufacture and sale restrictions",
            "false claims prohibition",
            "imitation restrictions",
        ],
    ),
    Chunk(
        chunk_id="SEC-18",
        service="Licensing and Enforcement",
        standard="BIS Act, 2016 - Section 18",
        clause="Obligations and Enforcement (Section 18)",
        title="Licensee Responsibilities, Distributor Duties, and Recalls",
        text=(
            "A licence holder remains entirely responsible at all times for ensuring standard-marked goods conform to standards[cite: 1]. "
            "Distributors and sellers must ensure products are procured exclusively from certified bodies and verify all labels and markings[cite: 1]. "
            "If the Bureau finds items non-conforming, it can direct halt of supply, market recalls, repairs, replacement, "
            "reprocessing, or consumer compensation[cite: 1]."
        ),
        source="BIS Act, 2016, Section 18[cite: 1]",
        keywords=[
            "section 18",
            "obligations and enforcement",
            "licensee responsibility",
            "distributor and seller duties",
            "recalls and non-conformance",
        ],
    ),
    # ---------------- Licensing & Penalties ----------------
    Chunk(
        chunk_id="LIC-001",
        service="Licensing",
        standard="BIS (Conformity Assessment) Regulations, 2018",
        clause="Regulation 5",
        title="How to Apply for a BIS Licence",
        text=(
            "Manufacturers apply for a BIS product licence via the online "
            "portal (www.bis.gov.in / eBIS), submitting a test report from a "
            "BIS-recognised lab, factory details, and the applicable "
            "standard (IS number). Grant of licence typically follows a "
            "factory audit and sample testing."
        ),
        source="BIS (Conformity Assessment) Regulations, 2018, Regulation 5",
        keywords=[
            "apply",
            "license",
            "licence",
            "how to get bis license",
            "bis license apply",
            "new license",
            "ebis",
            "portal",
            "regulation 5",
        ],
    ),
    Chunk(
        chunk_id="LIC-002",
        service="Licensing",
        standard="BIS Act, 2016 - Section 29 & 31",
        clause="Section 29 & 31",
        title="Penalties and Consumer Compensation for Non-Conforming Goods",
        text=(
            "Manufacture, sale, or import of goods under a notified "
            "standard without a valid BIS licence/ISI mark is punishable "
            "with imprisonment up to two years and/or heavy fines under Section 29 of the BIS Act, 2016[cite: 1]. "
            "Furthermore, under Section 31, licensees selling non-conforming goods "
            "or items failing expiration/quality standards are liable to compensate consumers for injury caused[cite: 1]."
        ),
        source="Bureau of Indian Standards Act, 2016, Sections 29 & 31[cite: 1]",
        keywords=[
            "penalty",
            "punishment",
            "without license",
            "illegal",
            "fine",
            "jail",
            "bis act",
            "compensation",
            "consumer protection",
            "section 29 & 31",
        ],
    ),
]


# ---------------------------------------------------------------------------
# 2. PDF INGESTION (real BIS documents, optional)
#
# Drop official BIS standard PDFs into data/raw_pdfs/ and they will be
# extracted, cleaned, chunked along clause boundaries, and merged into the
# same knowledge base as the curated Chunks above.
# ---------------------------------------------------------------------------

CLAUSE_HEADING_RE = re.compile(r"(?m)^\s*(\d+(?:\.\d+){0,3})\s+([A-Z][^\n]{3,120})$")
STANDARD_NUMBER_RE = re.compile(r"\bIS[\s\-]?\d{2,6}(?:\s*\(Part\s*\d+\))?(?:\s*[:\-]\s*\d{4})?\b", re.IGNORECASE)


def load_pdfs(folder_path: str = config.RAW_PDF_DIR) -> List[dict]:
    """Read every PDF in folder_path and return raw per-page text.

    Returns a list of {"source_file": ..., "pages": [page_text, ...]}.
    Uses PyMuPDF (fitz) because, unlike plain text extraction, it keeps
    layout well enough to preserve clause numbering, which BIS documents
    rely on for structure.
    """
    results = []
    if not os.path.isdir(folder_path):
        return results

    try:
        import fitz  # PyMuPDF
    except ImportError:
        # PDF ingestion is optional; the curated knowledge base above still
        # works without this dependency installed.
        return results

    for pdf_path in sorted(glob.glob(os.path.join(folder_path, "*.pdf"))):
        try:
            doc = fitz.open(pdf_path)
            pages = [page.get_text("text") for page in doc]
            doc.close()
            results.append({"source_file": os.path.basename(pdf_path), "pages": pages})
        except Exception as exc:  # noqa: BLE001 - surfaced to the caller/UI
            results.append({"source_file": os.path.basename(pdf_path), "pages": [], "error": str(exc)})
    return results


def clean_text(raw_text: str) -> str:
    """Strip page-number/header noise while preserving clause numbering."""
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse runs of blank lines and trailing spaces.
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Drop standalone page-number-only lines (e.g. "12" or "Page 12 of 40").
    text = re.sub(r"(?m)^\s*(page\s*)?\d{1,4}(\s*of\s*\d{1,4})?\s*$", "", text, flags=re.IGNORECASE)
    return text.strip()


def extract_metadata(pdf_path: str, text: str) -> dict:
    """Best-effort extraction of the IS standard number and a title."""
    filename = os.path.basename(pdf_path)
    match = STANDARD_NUMBER_RE.search(text) or STANDARD_NUMBER_RE.search(filename)
    standard_number = match.group(0).strip() if match else filename.rsplit(".", 1)[0]

    # First reasonably long line is used as a rough title.
    title = next((ln.strip() for ln in text.splitlines() if len(ln.strip()) > 8), filename)
    return {"standard_number": standard_number, "title": title[:150], "source_file": filename}


def chunk_text(text: str, chunk_size: int = config.PDF_CHUNK_SIZE, overlap: int = config.PDF_CHUNK_OVERLAP) -> List[dict]:
    """Chunk along detected clause headings first, falling back to a sliding
    window when the document has no obvious numbered structure.

    Returns a list of {"clause": ..., "text": ...}.
    """
    headings = list(CLAUSE_HEADING_RE.finditer(text))
    chunks = []

    if headings:
        for i, m in enumerate(headings):
            start = m.start()
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
            body = text[start:end].strip()
            if body:
                chunks.append({"clause": m.group(1), "text": body[: chunk_size * 3]})
    else:
        step = max(chunk_size - overlap, 1)
        for i in range(0, len(text), step):
            body = text[i:i + chunk_size].strip()
            if body:
                chunks.append({"clause": "N/A", "text": body})
    return chunks


def build_chunks_from_pdfs(folder_path: str = config.RAW_PDF_DIR) -> List[Chunk]:
    """Full PDF -> Chunk pipeline: load, clean, chunk, tag with metadata."""
    pdf_chunks: List[Chunk] = []
    for doc in load_pdfs(folder_path):
        if doc.get("error") or not doc["pages"]:
            continue
        full_text = clean_text("\n".join(doc["pages"]))
        meta = extract_metadata(doc["source_file"], full_text)
        for idx, piece in enumerate(chunk_text(full_text)):
            pdf_chunks.append(
                Chunk(
                    chunk_id=f"PDF-{meta['standard_number']}-{idx}",
                    service="Ingested BIS Document",
                    standard=meta["standard_number"],
                    clause=f"Clause {piece['clause']}" if piece["clause"] != "N/A" else "N/A",
                    title=meta["title"],
                    text=piece["text"],
                    source=f"{meta['standard_number']}, {meta['title']} (source: {meta['source_file']})",
                    keywords=[],
                )
            )
    return pdf_chunks


def get_all_chunks() -> List[Chunk]:
    """Curated seed chunks + anything ingested from data/raw_pdfs/."""
    return KNOWLEDGE_BASE + build_chunks_from_pdfs()


# ---------------------------------------------------------------------------
# 3. EMBEDDINGS + CHROMADB STORAGE
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Loading BIS knowledge base...")
def get_chroma_collection():
    """Build (or load) a persistent ChromaDB collection of all chunks.

    Cached with st.cache_resource so this expensive step (embedding every
    chunk) only runs once per server process, not on every user query.
    Uses Chroma's bundled local embedding model (all-MiniLM-L6-v2 via
    onnxruntime) so retrieval works even without a Gemini API key - only
    the final answer generation step needs Gemini.
    """
    import chromadb

    client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
    collection = client.get_or_create_collection(name=config.COLLECTION_NAME)

    chunks = get_all_chunks()
    existing_ids = set(collection.get(include=[])["ids"]) if collection.count() > 0 else set()
    new_chunks = [c for c in chunks if c.chunk_id not in existing_ids]

    if new_chunks:
        collection.upsert(
            ids=[c.chunk_id for c in new_chunks],
            documents=[f"{c.title}\n{c.text}" for c in new_chunks],
            metadatas=[
                {
                    "service": c.service,
                    "standard": c.standard,
                    "clause": c.clause,
                    "title": c.title,
                    "source": c.source,
                }
                for c in new_chunks
            ],
        )
    return collection, {c.chunk_id: c for c in chunks}
