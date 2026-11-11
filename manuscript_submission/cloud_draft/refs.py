"""Reference database for the manuscript.

Each entry holds the bibliographic fields exactly as confirmed in the source named in
``bib_src`` together with the outcome of the content check (``claim`` = what the manuscript
uses the reference for, ``content`` = what was actually read and what it supports).
``references.bib`` and ``REFERENCE_VERIFICATION.md`` are generated from this file, and the
numbered reference list in the DOCX is formatted from it in MDPI style.

Levels used in ``level``:
  A  bibliographic record confirmed AND abstract/full text read; it supports the stated use
  B  bibliographic record confirmed; abstract not obtainable, use limited to what the title/scope states
  C  authoritative web page or standard confirmed by its issuing body's page or DOI record
"""

ACCESSED = "11 November 2026"

REFS = {
    # ------------------------------------------------------------------ sensors and their faults
    "fraden2016": dict(
        type="book", authors=["Fraden, J."], title="Handbook of Modern Sensors: Physics, Designs, and Applications",
        publisher="Springer", address="Cham, Switzerland", year=2016, doi="10.1007/978-3-319-19303-8",
        bib_src="Crossref record of the DOI (author, title, subtitle, publisher, place, year, ISBN 978-3-319-19302-1). "
                "The record gives no edition statement, so none is printed.",
        claim="General background: a sensing element is followed by interface (signal-conditioning) electronics and a converter.",
        content="Book; not read for this manuscript. Cited only as a general handbook.", level="B"),
    "li2020": dict(
        type="article", authors=["Li, D.", "Wang, Y.", "Wang, J.", "Wang, C.", "Duan, Y."],
        title="Recent advances in sensor fault diagnosis: A review", journal="Sens. Actuators A Phys.",
        journal_full="Sensors and Actuators A: Physical", year=2020, volume="309", pages="111990",
        doi="10.1016/j.sna.2020.111990",
        bib_src="Crossref record of the DOI.",
        claim="Review of sensor fault types and of model-based and data-driven sensor fault diagnosis.",
        content="Abstract (Semantic Scholar): \"The paper introduces the common fault types and causes in sensors\" and gives "
                "\"a comprehensive review on the contemporary fault diagnosis techniques\". Supports the use.", level="A"),
    "balaban2009": dict(
        type="article", authors=["Balaban, E.", "Saxena, A.", "Bansal, P.", "Goebel, K.F.", "Curran, S."],
        title="Modeling, Detection, and Disambiguation of Sensor Faults for Aerospace Applications",
        journal="IEEE Sens. J.", journal_full="IEEE Sensors Journal", year=2009, volume="9", pages="1907–1917",
        doi="10.1109/JSEN.2009.2030284",
        bib_src="Crossref record of the DOI.",
        claim="Sensor faults such as bias, drift, scaling and dropout; the need to distinguish sensor faults from faults of the monitored system.",
        content="Abstract (OpenAlex, reconstructed): faults \"such as bias, drift, scaling, and dropout were injected\"; aim to "
                "\"distinguish between sensor faults and system faults\". Supports the use. Noise faults are not mentioned, "
                "so the manuscript does not attribute them to this source.", level="A"),
    "henry1993": dict(
        type="article", authors=["Henry, M.P.", "Clarke, D.W."],
        title="The self-validating sensor: rationale, definitions and examples", journal="Control Eng. Pract.",
        journal_full="Control Engineering Practice", year=1993, volume="1", pages="585–610",
        doi="10.1016/0967-0661(93)91382-7",
        bib_src="Crossref record of the DOI.",
        claim="A self-validating sensor performs internal diagnostics and reports the on-line uncertainty of each measurement.",
        content="Abstract (Oxford University Research Archive copy): the sensor \"generates a variety of data types, including the "
                "on-line uncertainty of each measurement\". Supports the use.", level="A"),
    "feng2007": dict(
        type="article", authors=["Feng, Z.", "Wang, Q.", "Shida, K."],
        title="A review of self-validating sensor technology", journal="Sens. Rev.", journal_full="Sensor Review",
        year=2007, volume="27", pages="48–56", doi="10.1108/02602280710723488",
        bib_src="Crossref record of the DOI.",
        claim="Review of self-validating sensor technology.",
        content="Abstract (Crossref): \"To provide an overview of self-validating sensor technology for researchers and engineers\". "
                "Supports the use.", level="A"),
    "isermann2006": dict(
        type="book", authors=["Isermann, R."], title="Fault-Diagnosis Systems", publisher="Springer",
        address="Berlin/Heidelberg, Germany", year=2006, doi="10.1007/3-540-30368-5",
        bib_src="Crossref record of the DOI (author, title, publisher, place, year, ISBN 978-3-540-24112-6). The record carries "
                "no subtitle, so none is printed.",
        claim="General reference for fault detection and diagnosis (detection, isolation, identification).",
        content="Book; not read for this manuscript. Cited only as a general textbook.", level="B"),
    "mccarthy2022": dict(
        type="web", authors=["McCarthy, M.", "Shaikh, W."],
        title="How to Design and Certify Functionally Safe Resistance Temperature Detector (RTD) Systems",
        publisher="Analog Devices", year=2022, note="Technical article, 21 July 2022",
        url="https://www.analog.com/en/resources/technical-articles/design-and-certify-functionally-safe-rtd-systems.html",
        bib_src="Publisher page (title, authors, date \"Jul 21 2022\").",
        claim="Commercial signal-chain converters embed diagnostics such as reference detection, an internal test voltage that "
              "checks the gain stage, and burnout currents for sensor connectivity.",
        content="Page text read: reference detect \"will indicate that the reference voltage is too low\"; an internal 20 mV input "
                "checks the gain stage; burnout currents check sensor connectivity; embedded diagnostics \"eliminate the need for "
                "signal chain duplication for diagnostic purposes\". Supports the use.", level="A"),
    "adi_an1320": dict(
        type="web", authors=["Analog Devices"], title="AN-1320: ADuCM360/ADuCM361 Self Diagnostic Features",
        publisher="Analog Devices", year=None, note="Application note",
        url="https://www.analog.com/en/resources/app-notes/an-1320.html",
        bib_src="Publisher page (title, document number). No author, revision or date is shown on the page; the PDF could not "
                "be fetched, so no year is printed.",
        claim="Microcontroller-integrated converters provide diagnostic current sources for open- and short-circuit detection "
              "and checks of the external reference.",
        content="Page text read: diagnostic current sources for open/short detection, input-multiplexer cross-checks and "
                "external-reference checks that \"diagnose issues with the ADuCM360/ADuCM361 and surrounding circuitry\". "
                "Supports the use. The page does not describe separating sensor faults from electronics faults.", level="A"),
    # ------------------------------------------------------------------ built-in self-test
    "hantos2021": dict(
        type="article", authors=["Hantos, G.", "Flynn, D.", "Desmulliez, M.P.Y."],
        title="Built-In Self-Test (BIST) Methods for MEMS: A Review", journal="Micromachines", journal_full="Micromachines",
        year=2021, volume="12", pages="40", doi="10.3390/mi12010040",
        bib_src="Crossref record of the DOI (volume 12, issue 1, article 40; published online 31 December 2020, issue dated "
                "January 2021; cited with the issue year as the journal does).",
        claim="Review and taxonomy of built-in self-test methods for MEMS sensors.",
        content="Abstract (Crossref): \"A novel taxonomy of built-in self-test (BIST) methods is presented\". Supports the use.",
        level="A"),
    "mir2006": dict(
        type="article", authors=["Mir, S.", "Rufer, L.", "Dhayni, A."], title="Built-in-self-test techniques for MEMS",
        journal="Microelectron. J.", journal_full="Microelectronics Journal", year=2006, volume="37", pages="1591–1597",
        doi="10.1016/j.mejo.2006.04.016",
        bib_src="Crossref record of the DOI.",
        claim="Built-in self-test techniques for MEMS devices (named as an example of BIST at the transducer).",
        content="Abstract not obtainable (index rate limits). Use limited to the scope stated by the title.", level="B"),
    "deb2006": dict(
        type="article", authors=["Deb, N.", "Blanton, R.D."], title="Built-In Self-Test of MEMS Accelerometers",
        journal="J. Microelectromech. Syst.", journal_full="Journal of Microelectromechanical Systems", year=2006,
        volume="15", pages="52–68", doi="10.1109/JMEMS.2006.864239",
        bib_src="Crossref title search (the DOI first tried, 10.1109/JMEMS.2005.864239, does not exist; the record found is "
                "10.1109/JMEMS.2006.864239).",
        claim="Built-in self-test of MEMS accelerometers (named as an example of BIST at the transducer).",
        content="Abstract not obtainable (index rate limits). Use limited to the scope stated by the title.", level="B"),
    "alraho2022": dict(
        type="article", authors=["Alraho, S.", "Zaman, Q.", "Abd, H.", "König, A."],
        title="Integrated Sensor Electronic Front-Ends with Self-X Capabilities", journal="Chips", journal_full="Chips",
        year=2022, volume="1", pages="83–120", doi="10.3390/chips1020008",
        bib_src="Crossref record of the DOI.",
        claim="Sensor front-ends with self-monitoring, self-trimming and self-healing functions.",
        content="Abstract (Crossref): \"self-monitoring, -trimming, or -healing\". Supports the use.", level="A"),
    "ieee1149_4": dict(
        type="standard", designation="IEEE Std 1149.4-2010", title="IEEE Standard for a Mixed-Signal Test Bus",
        publisher="IEEE", address="Piscataway, NJ, USA", year=2011, doi="10.1109/IEEESTD.2011.5738198",
        bib_src="Crossref record of the DOI (title, publisher, place, approval date 8 December 2010). The designation is not in "
                "the record; it follows IEEE's numbering for the mixed-signal test bus standard and its 2010 approval.",
        claim="A standardized analog test bus gives test access to analog nodes of mixed-signal devices.",
        content="Standard; no abstract in the record. Use limited to the scope stated by the title.", level="C"),
    "pavlidis2021": dict(
        type="article", authors=["Pavlidis, A.", "Louërat, M.-M.", "Faehn, E.", "Kumar, A.", "Stratigopoulos, H.-G."],
        title="SymBIST: Symmetry-Based Analog and Mixed-Signal Built-In Self-Test for Functional Safety",
        journal="IEEE Trans. Circuits Syst. I Regul. Pap.",
        journal_full="IEEE Transactions on Circuits and Systems I: Regular Papers", year=2021, volume="68",
        pages="2580–2593", doi="10.1109/TCSI.2021.3067180",
        bib_src="Crossref title search (authors, volume 68, issue 6, pages 2580–2593, June 2021). Crossref spells the second "
                "author \"Louerat\"; the accented form used by the author is printed.",
        claim="Built-in self-test of analog and mixed-signal integrated circuits based on invariant signals, demonstrated on a SAR ADC.",
        content="Abstract (Semantic Scholar): \"SymBIST exploits inherent symmetries in an A/M-S IC to construct signals that are "
                "invariant by default\"; demonstrated \"on a Successive Approximation Register (SAR) Analog-to-Digital Converter\". "
                "Supports the use.", level="A"),
    "ganji2024": dict(
        type="article", authors=["Ganji, M.", "Saikiran, M.", "Bhatheja, K.", "Chen, D."],
        title="Digital-like built-in defect-oriented test for analog-mixed signal circuits", journal="Design+",
        journal_full="Design+", year=2024, volume="1", pages="4351", doi="10.36922/dp.4351",
        bib_src="Crossref record of the DOI and publisher page (volume 1, issue 1, article 4351, 18 November 2024).",
        claim="Defect-oriented built-in self-test for analog and mixed-signal circuits.",
        content="Abstract (publisher page): \"a novel digital-like defect-oriented built-in self-test (BIST) methodology for analog "
                "and mixed-signal (AMS) circuits\". Supports the use.", level="A"),
    "sunter2016": dict(
        type="article", authors=["Sunter, S.", "Jurga, K.", "Laidler, A."],
        title="Using Mixed-Signal Defect Simulation to Close the Loop Between Design and Test",
        journal="IEEE Trans. Circuits Syst. I Regul. Pap.",
        journal_full="IEEE Transactions on Circuits and Systems I: Regular Papers", year=2016, volume="63",
        pages="2313–2322", doi="10.1109/TCSI.2016.2616159",
        bib_src="Crossref title search (the DOI first tried was wrong; the record found is 10.1109/TCSI.2016.2616159).",
        claim="Defect simulation is used to assess tests of mixed-signal circuits.",
        content="Abstract not obtainable (elided by the publisher in the indexes). Use limited to the scope stated by the title.",
        level="B"),
    # ------------------------------------------------------------------ ADC test and imperfect stimuli
    "ieee1241": dict(
        type="standard", designation="IEEE Std 1241-2010",
        title="IEEE Standard for Terminology and Test Methods for Analog-to-Digital Converters",
        publisher="IEEE", address="Piscataway, NJ, USA", year=2011, doi="10.1109/IEEESTD.2011.5692956",
        bib_src="Crossref record of the DOI (title, publisher, place, approval date 17 June 2010). The designation is not in the "
                "record. A later revision exists (DOI 10.1109/IEEESTD.2023.10269815, approved 5 June 2023); the authors may "
                "prefer to cite it.",
        claim="Standard terminology and test methods for ADCs, including static gain and offset.",
        content="Standard; no abstract in the record. Use limited to the scope stated by the title.", level="C"),
    "jin2005": dict(
        type="article", authors=["Jin, L.", "Parthasarathy, K.", "Kuyel, T.", "Chen, D.", "Geiger, R.L."],
        title="Accurate Testing of Analog-to-Digital Converters Using Low Linearity Signals With Stimulus Error Identification and Removal",
        journal="IEEE Trans. Instrum. Meas.", journal_full="IEEE Transactions on Instrumentation and Measurement",
        year=2005, volume="54", pages="1188–1199", doi="10.1109/TIM.2005.847240",
        bib_src="Crossref record of the DOI.",
        claim="ADC linearity can be tested with an imprecise stimulus when the stimulus error is identified and removed.",
        content="Abstract (OpenAlex): signal \"generators that may be significantly less linear than the ADC under test\". "
                "Supports the use.", level="A"),
    "chen2018": dict(
        type="article", authors=["Chen, T.", "Jin, X.", "Geiger, R.L.", "Chen, D."],
        title="USER-SMILE: Ultrafast Stimulus Error Removal and Segmented Model Identification of Linearity Errors for ADC Built-in Self-Test",
        journal="IEEE Trans. Circuits Syst. I Regul. Pap.",
        journal_full="IEEE Transactions on Circuits and Systems I: Regular Papers", year=2018, volume="65",
        pages="2059–2069", doi="10.1109/TCSI.2017.2775632",
        bib_src="Crossref record of the DOI (volume 65, issue 7, print July 2018).",
        claim="ADC built-in self-test that tolerates a low-accuracy on-chip stimulus by removing the stimulus error.",
        content="Abstract (OpenAlex): a stimulus \"error removal technique is used to recover\" the test accuracy for \"on-chip "
                "built-in self-test\". Supports the use.", level="A"),
    # ------------------------------------------------------------------ closest prior work
    "czaja2013": dict(
        type="article", authors=["Czaja, Z."],
        title="Self-Testing of Analog Parts Terminated by ADCs Based on Multiple Sampling of Time Responses",
        journal="IEEE Trans. Instrum. Meas.", journal_full="IEEE Transactions on Instrumentation and Measurement",
        year=2013, volume="62", pages="3160–3167", doi="10.1109/TIM.2013.2272867",
        bib_src="Crossref title search (volume 62, issue 12, December 2013).",
        claim="Self-test of an analog part terminated by an ADC in a microcontroller system: voltage samples of the response to a "
              "square pulse are mapped to localization curves for detection and single soft-fault localization.",
        content="Abstract (OpenAlex, reconstructed): \"self-testing of analog parts terminated by analog-to-digital converters in "
                "mixed-signal electronic microsystems controlled by microcontrollers\"; \"fault detection and single soft fault "
                "localization\"; experimental verification included. Supports the use. Faults of the ADC or of a sensor are not "
                "mentioned in the abstract.", level="A"),
    "czaja2016": dict(
        type="article", authors=["Czaja, Z."],
        title="A method of self-testing of an analog circuit terminated by an ADC in electronic embedded systems controlled by microcontrollers",
        journal="Prz. Elektrotech.", journal_full="Przegląd Elektrotechniczny", year=2016, volume="92", pages="19–22",
        doi="10.15199/48.2016.11.05",
        bib_src="Full text (author's institutional repository copy: header \"R. 92 NR 11/2016\", pages 19–22) and OpenAlex record "
                "of the DOI. OpenAlex lists volume 1 and pages 21–24; the article itself is taken as authoritative.",
        claim="Microcontroller-generated square pulse, 64 samples of the time response of a Sallen–Key filter, fault dictionary "
              "generated by simulation, sampling instants triggered by the timer that generates the pulse.",
        content="Full text read: 2 ms square pulse from the microcontroller, N = 64 samples, second-order Sallen–Key low-pass "
                "filter, \"The method can be used for fault detection and single soft fault localization\"; conversions are "
                "triggered by the same timer as the pulse. ADC and sensor faults are not addressed. Supports the use.", level="A"),
    # ------------------------------------------------------------------ data-driven analog fault diagnosis
    "aminian2000": dict(
        type="article", authors=["Aminian, M.", "Aminian, F."],
        title="Neural-network based analog-circuit fault diagnosis using wavelet transform as preprocessor",
        journal="IEEE Trans. Circuits Syst. II Analog Digit. Signal Process.",
        journal_full="IEEE Transactions on Circuits and Systems II: Analog and Digital Signal Processing", year=2000,
        volume="47", pages="151–156", doi="10.1109/82.823545",
        bib_src="Crossref record of the DOI.",
        claim="Features extracted from the circuit response by wavelet decomposition are classified by a neural network.",
        content="Abstract (OpenAlex, reconstructed): \"using wavelet decomposition, principal component analysis, and data "
                "normalization as preprocessors\". Supports the use.", level="A"),
    "binu2017": dict(
        type="article", authors=["Binu, D.", "Kariyappa, B.S."],
        title="A survey on fault diagnosis of analog circuits: Taxonomy and state of the art",
        journal="AEU Int. J. Electron. Commun.", journal_full="AEU - International Journal of Electronics and Communications",
        year=2017, volume="73", pages="68–83", doi="10.1016/j.aeue.2017.01.002",
        bib_src="Crossref record of the DOI.",
        claim="Survey of analog-circuit fault diagnosis.",
        content="No abstract in any index consulted. Use limited to the scope stated by the title.", level="B"),
    "zhao2018": dict(
        type="article", authors=["Zhao, G.", "Liu, X.", "Zhang, B.", "Liu, Y.", "Niu, G.", "Hu, C."],
        title="A novel approach for analog circuit fault diagnosis based on Deep Belief Network", journal="Measurement",
        journal_full="Measurement", year=2018, volume="121", pages="170–178", doi="10.1016/j.measurement.2018.02.044",
        bib_src="Crossref record of the DOI.",
        claim="A deep belief network learns features from raw time-series responses of analog circuits.",
        content="Abstract (Semantic Scholar): the network \"extracts features adaptively from the raw time series signals\". "
                "Supports the use.", level="A"),
    "yang2020": dict(
        type="article", authors=["Yang, H.", "Meng, C.", "Wang, C."],
        title="Data-Driven Feature Extraction for Analog Circuit Fault Diagnosis Using 1-D Convolutional Neural Network",
        journal="IEEE Access", journal_full="IEEE Access", year=2020, volume="8", pages="18305–18315",
        doi="10.1109/ACCESS.2020.2968744",
        bib_src="Crossref record of the DOI.",
        claim="A 1-D CNN classifies raw circuit responses; evaluated on simulated benchmark circuits.",
        content="Abstract (OpenAlex, reconstructed): raw signals are fed to the network, which is \"evaluated through three "
                "benchmark circuits based on SIMULINK platform\". Supports the use.", level="A"),
    "zhang2021": dict(
        type="article", authors=["Zhang, C.", "Zha, D.", "Wang, L.", "Mu, N."],
        title="A Novel Analog Circuit Soft Fault Diagnosis Method Based on Convolutional Neural Network and Backward Difference",
        journal="Symmetry", journal_full="Symmetry", year=2021, volume="13", pages="1096", doi="10.3390/sym13061096",
        bib_src="Crossref record of the DOI and publisher page.",
        claim="CNN-based soft-fault diagnosis on Sallen–Key and four-op-amp biquad filter benchmarks.",
        content="Publisher page read: Sallen–Key band-pass and four-op-amp biquad high-pass filters; response and its backward "
                "differences fed to a CNN. Supports the use. (The abstract says \"measured\" responses while the body describes "
                "OrCAD simulation; the manuscript does not rely on that detail for this paper.)", level="A"),
    "yang2023": dict(
        type="article", authors=["Yang, J.", "Gao, T.", "Jiang, S."],
        title="A Dual-input Fault Diagnosis Model Based on SE-MSCNN for Analog Circuits", journal="Appl. Intell.",
        journal_full="Applied Intelligence", year=2023, volume="53", pages="7154–7168", doi="10.1007/s10489-022-03665-3",
        bib_src="Crossref record of the DOI (online 15 July 2022; volume 53, issue 6, March 2023).",
        claim="Multi-scale CNN with squeeze-and-excitation applied to responses of analog circuits under test.",
        content="Abstract (publisher page): dual-input time–frequency model; \"Three typical circuits are chosen as CUTs\". "
                "Supports the use.", level="A"),
    "gao2024": dict(
        type="article", authors=["Gao, J.", "Guo, J.", "Yuan, F.", "Yi, T.", "Zhang, F.", "Shi, Y.", "Li, Z.", "Ke, Y.", "Meng, Y."],
        title="An Exploration into the Fault Diagnosis of Analog Circuits Using Enhanced Golden Eagle Optimized "
              "1D-Convolutional Neural Network (CNN) with a Time-Frequency Domain Input and Attention Mechanism",
        journal="Sensors", journal_full="Sensors", year=2024, volume="24", pages="390", doi="10.3390/s24020390",
        bib_src="Crossref record of the DOI and publisher page.",
        claim="1-D CNN with attention; simulated four-op-amp filter with Monte Carlo samples; reported accuracy 98.93%.",
        content="Abstract (publisher page): \"Monte Carlo analysis is used to obtain a large number of samples\"; \"achieved a "
                "98.93% classification accuracy\". Supports the use.", level="A"),
    "shang2024": dict(
        type="article", authors=["Shang, Y.", "Wei, S.", "Li, C.", "Ye, X.", "Zeng, L.", "Hu, W.", "He, X.", "Zhou, J."],
        title="An End-to-End Mutually Exclusive Autoencoder Method for Analog Circuit Fault Diagnosis",
        journal="J. Electron. Test.", journal_full="Journal of Electronic Testing", year=2024, volume="40", pages="5–18",
        doi="10.1007/s10836-023-06097-0",
        bib_src="Crossref record of the DOI and full text (journal copy).",
        claim="Autoencoder features with a support-vector classifier on a four-op-amp biquad filter; verified on a simulated and "
              "an actual circuit.",
        content="Full text read: wavelet-packet and Fourier features, mutually exclusive autoencoders, SVM; the abstract states the "
                "method is \"verified by the simulation circuit and actual circuit\". Supports the use.", level="A"),
    "zhang2024": dict(
        type="article", authors=["Zhang, C.", "Du, P.", "Zhou, D.", "Dong, Z.", "He, S.", "Zhou, Z."],
        title="Fault Diagnosis of Low-Noise Amplifier Circuit Based on Fusion Domain Adaptation Method", journal="Actuators",
        journal_full="Actuators", year=2024, volume="13", pages="379", doi="10.3390/act13090379",
        bib_src="Publisher page (authors, volume 13, issue 9, article 379, 23 September 2024). The Crossref fetch of this DOI failed.",
        claim="Diagnosis accuracy of an analog circuit degrades when operating conditions differ between training and use; "
              "domain adaptation is applied.",
        content="Abstract (publisher page): cross-domain diagnosis \"under varying external or internal conditions\". Supports the "
                "use in these general terms.", level="A"),
    "afacan2021": dict(
        type="article", authors=["Afacan, E.", "Lourenço, N.", "Martins, R.", "Dündar, G."],
        title="Review: Machine learning techniques in analog/RF integrated circuit design, synthesis, layout, and test",
        journal="Integration", journal_full="Integration", year=2021, volume="77", pages="113–130",
        doi="10.1016/j.vlsi.2020.11.006",
        bib_src="Crossref record of the DOI.",
        claim="Review of machine learning in analog/RF circuit design and test.",
        content="Abstract (Semantic Scholar): \"a comprehensive review on ML techniques for analog/RF circuit modeling, design, "
                "synthesis, layout, and test\". Supports the use.", level="A"),
    "roy2021": dict(
        type="inproceedings", authors=["Roy, S.", "Millican, S.K.", "Agrawal, V.D."],
        title="Special Session – Machine Learning in Test: A Survey of Analog, Digital, Memory, and RF Integrated Circuits",
        booktitle="Proceedings of the 2021 IEEE 39th VLSI Test Symposium (VTS)", address="San Diego, CA, USA",
        dates="25–28 April 2021", year=2021, pages="1–14", doi="10.1109/VTS50974.2021.9441051",
        bib_src="Crossref record of the DOI and full text (author-hosted copy).",
        claim="Survey of machine learning in integrated-circuit test, including analog and RF test.",
        content="Abstract (full text): the survey \"examines applications of ML to testing analog, digital, memory, radio frequency "
                "(RF)\" circuits. Supports the use.", level="A"),
    "stratigopoulos2018": dict(
        type="inproceedings", authors=["Stratigopoulos, H.-G."], title="Machine learning applications in IC testing",
        booktitle="Proceedings of the 2018 IEEE 23rd European Test Symposium (ETS)", address="Bremen, Germany",
        dates="28 May–1 June 2018", year=2018, pages="1–10", doi="10.1109/ETS.2018.8400701",
        bib_src="Crossref record of the DOI.",
        claim="Overview of machine-learning applications in integrated-circuit testing.",
        content="Abstract not obtainable (elided by the publisher in the indexes). Use limited to the scope stated by the title.",
        level="B"),
    # ------------------------------------------------------------------ transfer between domains
    "tobin2017": dict(
        type="inproceedings", authors=["Tobin, J.", "Fong, R.", "Ray, A.", "Schneider, J.", "Zaremba, W.", "Abbeel, P."],
        title="Domain randomization for transferring deep neural networks from simulation to the real world",
        booktitle="Proceedings of the 2017 IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)",
        address="Vancouver, BC, Canada", dates="September 2017", year=2017, pages="23–30",
        doi="10.1109/IROS.2017.8202133",
        bib_src="Crossref record of the DOI (the record gives the month but not the days of the conference).",
        claim="Randomizing nuisance properties of the simulator during training so that a model transfers to another domain.",
        content="Abstract (arXiv:1703.06907, same paper): \"training models on simulated images that transfer to real images by "
                "randomizing rendering in the simulator\". Supports the use as an analogy; the paper randomizes rendering, not "
                "timing.", level="A"),
    "liw2022": dict(
        type="article", authors=["Li, W.", "Huang, R.", "Li, J.", "Liao, Y.", "Chen, Z.", "He, G.", "Yan, R.", "Gryllias, K."],
        title="A perspective survey on deep transfer learning for fault diagnosis in industrial scenarios: Theories, applications and challenges",
        journal="Mech. Syst. Signal Process.", journal_full="Mechanical Systems and Signal Processing", year=2022,
        volume="167", pages="108487", doi="10.1016/j.ymssp.2021.108487",
        bib_src="Crossref record of the DOI (eight authors; an author list recalled from memory was wrong and was replaced by the record).",
        claim="Survey of transfer learning for fault diagnosis under differences between training and deployment data.",
        content="No abstract in any index consulted. Use limited to the scope stated by the title.", level="B"),
    # ------------------------------------------------------------------ measurement and estimation
    "bellman1970": dict(
        type="article", authors=["Bellman, R.", "Åström, K.J."], title="On structural identifiability",
        journal="Math. Biosci.", journal_full="Mathematical Biosciences", year=1970, volume="7", pages="329–339",
        doi="10.1016/0025-5564(70)90132-X",
        bib_src="Crossref record of the DOI.",
        claim="The concept of structural identifiability of model parameters from input–output observations.",
        content="No abstract in any index consulted. Use limited to the concept named by the title.", level="B"),
    "jcgm100": dict(
        type="standard", designation="JCGM 100:2008",
        title="Evaluation of Measurement Data—Guide to the Expression of Uncertainty in Measurement",
        publisher="BIPM", address="Sèvres, France", year=2008, doi="10.59161/JCGM100-2008E",
        bib_src="Crossref record of the DOI (title, year, publisher BIPM) and its BIPM landing page.",
        claim="Framework for expressing the uncertainty of a measured quantity (here, the monitored reference level).",
        content="Guide; cited for the general framework only.", level="C"),
    "ieee181": dict(
        type="standard", designation="IEEE Std 181-2011", title="IEEE Standard for Transitions, Pulses, and Related Waveforms",
        publisher="IEEE", address="Piscataway, NJ, USA", year=2011, doi="10.1109/IEEESTD.2011.6016198",
        bib_src="Crossref record of the DOI (title, publisher, approval date 16 May 2011). The designation is not in the record.",
        claim="Standard definitions of transition parameters such as reference-level instants and transition durations.",
        content="Standard; no abstract in the record. Use limited to the scope stated by the title.", level="C"),
    "golub1973": dict(
        type="article", authors=["Golub, G.H.", "Pereyra, V."],
        title="The Differentiation of Pseudo-Inverses and Nonlinear Least Squares Problems Whose Variables Separate",
        journal="SIAM J. Numer. Anal.", journal_full="SIAM Journal on Numerical Analysis", year=1973, volume="10",
        pages="413–432", doi="10.1137/0710036",
        bib_src="Crossref record of the DOI.",
        claim="In separable least-squares problems the linear parameters can be eliminated and the fit carried out over the "
              "nonlinear parameters only.",
        content="Abstract (Crossref): \"it is possible to optimize first with respect to the parameters\" that enter linearly. "
                "Supports the use.", level="A"),
    "golub2003": dict(
        type="article", authors=["Golub, G.", "Pereyra, V."],
        title="Separable nonlinear least squares: the variable projection method and its applications",
        journal="Inverse Probl.", journal_full="Inverse Problems", year=2003, volume="19", pages="R1–R26",
        doi="10.1088/0266-5611/19/2/201",
        bib_src="Crossref record of the DOI.",
        claim="Review of the variable projection method.",
        content="Abstract (OpenAlex): \"we review 30 years of developments and applications of the variable projection method\". "
                "Supports the use.", level="A"),
    "oleary2013": dict(
        type="article", authors=["O'Leary, D.P.", "Rust, B.W."], title="Variable projection for nonlinear least squares problems",
        journal="Comput. Optim. Appl.", journal_full="Computational Optimization and Applications", year=2013,
        volume="54", pages="579–593", doi="10.1007/s10589-012-9492-9",
        bib_src="Crossref record of the DOI (online 2 August 2012; volume 54, issue 3, April 2013).",
        claim="Variable projection for separable nonlinear least squares.",
        content="No abstract in the indexes consulted. Use limited to the scope stated by the title.", level="B"),
    "bi1999": dict(
        type="article", authors=["Bi, Q.", "Cai, W.-J.", "Lee, E.-L.", "Wang, Q.-G.", "Hang, C.-C.", "Zhang, Y."],
        title="Robust identification of first-order plus dead-time model from step response", journal="Control Eng. Pract.",
        journal_full="Control Engineering Practice", year=1999, volume="7", pages="71–77",
        doi="10.1016/S0967-0661(98)00166-X",
        bib_src="Crossref record of the DOI.",
        claim="A first-order model with an unknown time delay can be identified from a sampled step response.",
        content="No abstract in the indexes consulted. Use limited to the scope stated by the title.", level="B"),
    "abdalmoaty2022": dict(
        type="preprint", authors=["Abdalmoaty, M.", "Medvedev, A."],
        title="Continuous Time-Delay Estimation From Sampled Measurements", year=2022, arxiv="2211.11053",
        url="https://arxiv.org/abs/2211.11053",
        bib_src="arXiv abstract page (v1, 20 November 2022; no journal reference or DOI listed).",
        claim="A delay that is a fraction of the sampling period can be estimated from sampled output data.",
        content="Abstract (arXiv): the method \"allows for the estimation of subsample delays\". Supports the use. Preprint.",
        level="A"),
    # ------------------------------------------------------------------ software
    "pedregosa2011": dict(
        type="article", authors=["Pedregosa, F.", "Varoquaux, G.", "Gramfort, A.", "et al."],
        title="Scikit-learn: Machine Learning in Python", journal="J. Mach. Learn. Res.",
        journal_full="Journal of Machine Learning Research", year=2011, volume="12", pages="2825–2830",
        url="https://jmlr.org/papers/v12/pedregosa11a.html",
        bib_src="Journal page (16 authors; first three printed followed by et al.).",
        claim="Software used for the classifier (scikit-learn).", content="Software reference.", level="C"),
    "kingma2015": dict(
        type="inproceedings", authors=["Kingma, D.P.", "Ba, J."], title="Adam: A Method for Stochastic Optimization",
        booktitle="Proceedings of the 3rd International Conference on Learning Representations (ICLR)",
        address="San Diego, CA, USA", dates="2015", year=2015, pages=None, url="https://arxiv.org/abs/1412.6980",
        bib_src="arXiv abstract page (comment: \"Published as a conference paper at the 3rd International Conference for Learning "
                "Representations, San Diego, 2015\").",
        claim="The Adam optimizer.", content="Method reference.", level="C"),
    "harris2020": dict(
        type="article", authors=["Harris, C.R.", "Millman, K.J.", "van der Walt, S.J.", "et al."],
        title="Array programming with NumPy", journal="Nature", journal_full="Nature", year=2020, volume="585",
        pages="357–362", doi="10.1038/s41586-020-2649-2",
        bib_src="Crossref record of the DOI (26 authors; first three printed followed by et al.).",
        claim="Software used (NumPy).", content="Software reference.", level="C"),
    "virtanen2020": dict(
        type="article", authors=["Virtanen, P.", "Gommers, R.", "Oliphant, T.E.", "et al."],
        title="SciPy 1.0: fundamental algorithms for scientific computing in Python", journal="Nat. Methods",
        journal_full="Nature Methods", year=2020, volume="17", pages="261–272", doi="10.1038/s41592-019-0686-2",
        bib_src="Crossref record of the DOI (first three authors printed followed by et al.).",
        claim="Software used (SciPy).", content="Software reference.", level="C"),
    "ngspice": dict(
        type="web", authors=["ngspice"], title="Open Source Spice Simulator, Release 47", publisher=None, year=2026,
        note=None, url="https://sourceforge.net/projects/ngspice/files/ng-spice-rework/",
        bib_src="Project file archive (ngspice-47.tar.gz, released 11 August 2026). The project's news page lists releases only "
                "up to 45.2; release 47 is confirmed by the file archive.",
        claim="Circuit simulator used for the netlist-level domain.", content="Software reference.", level="C"),
    # ------------------------------------------------------------------ evaluation and statistics
    "sokolova2009": dict(
        type="article", authors=["Sokolova, M.", "Lapalme, G."],
        title="A systematic analysis of performance measures for classification tasks", journal="Inf. Process. Manag.",
        journal_full="Information Processing & Management", year=2009, volume="45", pages="427–437",
        doi="10.1016/j.ipm.2009.03.002",
        bib_src="Crossref record of the DOI.",
        claim="Performance measures for multi-class classification (macro-averaged F1).",
        content="No abstract in the indexes consulted; the record carries the keyword \"multi-class classification\". Use limited "
                "to the scope stated by the title.", level="B"),
    "brodersen2010": dict(
        type="inproceedings", authors=["Brodersen, K.H.", "Ong, C.S.", "Stephan, K.E.", "Buhmann, J.M."],
        title="The Balanced Accuracy and Its Posterior Distribution",
        booktitle="Proceedings of the 2010 20th International Conference on Pattern Recognition", address="Istanbul, Turkey",
        dates="23–26 August 2010", year=2010, pages="3121–3124", doi="10.1109/ICPR.2010.764",
        bib_src="Crossref record of the DOI.",
        claim="Balanced accuracy as a measure that is not inflated by class imbalance.",
        content="Abstract (OpenAlex, reconstructed): conventional accuracy \"leads to an optimistic estimate when a biased "
                "classifier is tested on an imbalanced dataset\". Supports the use.", level="A"),
    "efron1993": dict(
        type="book", authors=["Efron, B.", "Tibshirani, R.J."], title="An Introduction to the Bootstrap",
        publisher="Chapman & Hall", address="New York, NY, USA", year=1993, doi="10.1007/978-1-4899-4541-9",
        bib_src="Crossref record of the DOI (authors, title, year 1993, print ISBN 978-0-412-04231-7). The record is deposited "
                "by Springer US, which hosts the digitized Chapman & Hall edition; the original imprint is printed.",
        claim="Bootstrap percentile confidence intervals.", content="Book; cited as the standard text.", level="B"),
    "field2007": dict(
        type="article", authors=["Field, C.A.", "Welsh, A.H."], title="Bootstrapping Clustered Data",
        journal="J. R. Stat. Soc. Ser. B Stat. Methodol.",
        journal_full="Journal of the Royal Statistical Society Series B: Statistical Methodology", year=2007,
        volume="69", pages="369–390", doi="10.1111/j.1467-9868.2007.00593.x",
        bib_src="Crossref record of the DOI.",
        claim="Bootstrap schemes for clustered data that resample at the cluster level.",
        content="Abstract (Crossref): \"the cluster bootstrap gives consistent estimates under both the transformation and the "
                "random-effect model\". Supports the use.", level="A"),
    "lai2018": dict(
        type="preprint", authors=["Lai, L.", "Suda, N.", "Chandra, V."],
        title="CMSIS-NN: Efficient Neural Network Kernels for Arm Cortex-M CPUs", year=2018, arxiv="1801.06601",
        url="https://arxiv.org/abs/1801.06601",
        bib_src="arXiv abstract page (v1, 19 January 2018).",
        claim="Neural-network inference kernels exist for Cortex-M class microcontrollers.",
        content="Abstract (arXiv): \"efficient kernels developed to maximize the performance and minimize the memory footprint of "
                "neural network (NN) applications on Arm Cortex-M processors\". Supports the use.", level="A"),
}

# Candidates that were examined and NOT used, with the reason (for REFERENCE_VERIFICATION.md).
DROPPED = [
    ("Kerzérho, V.; et al. Fully digital test solution for a set of ADCs and DACs embedded in a SIP or SOC. IET Comput. "
     "Digit. Tech. 2007, 1, 146–153 (DOI 10.1049/iet-cdt:20060136)",
     "Bibliographic record confirmed, but the abstract does not support the statement it was meant to carry (that a loopback "
     "configuration exposes only the combined error of two converters). The statement was removed from the manuscript."),
    ("Jombo, G.; Zhang, E.; Lu, N. Sensor Fault Detection and Diagnosis: Methods and Challenges. IFAC SAFEPROCESS 2024",
     "Only a repository record was found (no DOI, no page range, marked as not refereed). Replaced by the journal review of Li et al. (2020)."),
    ("Sun, Y.; He, Y.; Tan, Y. (2004), IEE Proceedings – Circuits, Devices and Systems (candidate from the earlier .bib file)",
     "Volume and pages could not be confirmed. Removed."),
    ("Kester, W. (Ed.) Data Conversion Handbook; Newnes: 2005",
     "Only chapter-level records were found and the editor statement could not be confirmed from a record. Not needed; IEEE Std 1241 is cited instead."),
    ("Pallàs-Areny, R.; Webster, J.G. Sensors and Signal Conditioning, 2nd ed.; Wiley: 2001",
     "No record found in Crossref. Replaced by Fraden (2016)."),
    ("Wang, Q.-G.; Zhang, Y. Robust identification of continuous systems with dead-time from step responses. Automatica 2001, 37, 377–390",
     "Record confirmed, abstract not obtainable. Redundant with Bi et al. (1999); not used."),
    ("Roy, S.; Millican, S.K.; Agrawal, V.D. A Survey and Recent Advances: Machine Intelligence in Electronic Testing. "
     "J. Electron. Test. 2024, 40, 139–158 (DOI 10.1007/s10836-024-06117-7)",
     "Record confirmed, full text not readable (blocked). Redundant with the 2021 survey by the same authors, which was read; not used."),
    ("Ramesh, J.; et al. Design and test of analog-to-digital converters with enhanced test strategies using built in self "
     "test. Sci. Rep. 2025, 15, 31909",
     "Record and abstract confirmed. Concerns the design of standalone ADC BIST circuitry and adds nothing to the argument beyond the cited ADC BIST work; not used."),
    ("Nosek, B.A.; et al. The preregistration revolution. Proc. Natl. Acad. Sci. USA 2018, 115, 2600–2606",
     "Record and abstract confirmed. Not used because the manuscript no longer describes the protocol as preregistered."),
    ("Efron, B. Bootstrap Methods: Another Look at the Jackknife. Ann. Stat. 1979, 7",
     "Record confirmed but without page numbers. Efron and Tibshirani (1993) is cited instead."),
    ("\"A transfer learning method for fault diagnosis of analog circuit\" (Harbin Institute of Technology record)",
     "The record could not be resolved (redirect to another host). Not used."),
    ("Entries of the earlier references.bib that were marked VERIFY and are not listed above",
     "Not carried over. Every reference in the manuscript was rebuilt from a fetched record."),
]
