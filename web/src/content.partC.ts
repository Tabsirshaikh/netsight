/**
 * Part C: all new editorial copy.
 * External statistics use the source lines supplied with the brief.
 * Measured NetSight values remain in content.ts.
 * Layout coordinates and animation parameters are not research measurements.
 */
export const partC = {
  nav: {
    problem: 'Why it matters',
    system: 'How it works',
    evidence: 'What is measured'
  },
  common: {
    design: 'Design / illustrative until measured',
    measured: 'Measured research results',
    measuredSource: 'Source: supplied NetSight research results · src/content.ts',
    architecture: 'Proposed architecture · not a field validation',
    source: 'Source',
    ap50: 'AP50 · higher is better',
    notSurvey: 'Procedural illustration · not survey imagery'
  },
  problem: {
    id: 'problem',
    eyebrow: 'The mission / Why this search matters',
    title: 'The seabed is hard to read.\nThe stakes are not.',
    intro: 'NetSight is a research software layer for side-scan survey review. Start with the problem it is trying to help agencies solve.',
    stats: [
      {
        value: '~1.82%',
        title: 'of fishing gear lost per year',
        detail: '95% confidence interval: 1.62–2.03%.',
        source: 'Source: Richardson et al. (2022) · annual fishing-gear loss estimate.'
      },
      {
        value: '43.17 ± 5.48%',
        title: 'of reef debris was abandoned nets',
        detail: 'A finding from the reef-debris study, not a global ocean proportion.',
        source: 'Source: Edward et al. (2020).'
      },
      {
        value: '~800 miles',
        title: 'of side-scan after X-Press Pearl',
        detail: 'INS Sarvekshak surveyed in Sri Lankan waters in 2021, at Sri Lanka’s request.',
        source: 'Source: INS Sarvekshak / MV X-Press Pearl response (2021), as supplied in the project brief.'
      }
    ],
    workflowTitle: 'The search does not end at the sonar.',
    workflow: ['Sonar survey', 'Human review', 'Suspect list', 'Diver check'],
    workflowSource: 'Workflow reference: supplied project video summary · current-search chapter.',
    suspects: '549 sonar suspects. Divers checked 176. Of those, 94 were real gear.',
    interpretation: 'About half of the suspects divers checked were real. Checking a contact has a real operational cost.',
    studySource: 'Source: Stolte et al. (2022) · Baltic ghost-gear campaign.',
    bridge: 'A useful system must help decide both where to inspect and where to search again.'
  },
  questions: {
    id: 'questions',
    eyebrow: 'The idea / Three different questions',
    title: 'Find it.\nTrust it. Search better.',
    intro: 'A detector score, a contact probability and a search-completeness estimate answer different questions. NetSight keeps them separate.',
    pillars: [
      {
        question: 'Is there a contact?',
        name: 'Net-aware evidence',
        body: 'Detection proposes a location. The proposed evidence layer examines texture, lines and shadows without making a shadow mandatory: a collapsed net may lack one.',
        status: 'Research detector + proposed net-aware evidence'
      },
      {
        question: 'How much should we trust it?',
        name: 'Conditional confidence',
        body: 'Calibration turns scores into probabilities only within its validated scope. Applicability determines whether a claim is calibrated, indicative or withdrawn.',
        status: 'Measured calibration results appear below'
      },
      {
        question: 'What might the search have missed?',
        name: 'Search completeness',
        body: 'The proposed probability-of-detection layer asks how observable a target was in each part of a survey. No contact is not the same as strong evidence of absence.',
        status: 'Design / illustrative until measured'
      }
    ],
    preparationTitle: 'Before the survey: prepare, then test.',
    preparation: [
      {
        title: 'Synthetic net injection',
        body: 'Proposed target injection studies net appearance, shape, shadow and range effects on seabed textures. Synthetic examples need checks against real targets.',
        status: 'Design / illustrative until measured'
      },
      {
        title: 'Detection-probability study',
        body: 'Study detection under range, seabed and quality changes before assigning spatial completeness. No measured Pd curve is supplied here.',
        status: 'Design / illustrative until measured'
      },
      {
        title: 'Dataset-specific calibration',
        body: 'Choose calibration per dataset; beta or Platt is usually best in the supplied project update. Do not assume one fitted calibrator transfers to every survey.',
        status: 'Method update: supplied project brief'
      }
    ],
    footer: 'The measured research and the proposed operational system are not the same claim.'
  },
  pipeline: {
    id: 'system',
    eyebrow: 'The system / Eight online stages',
    title: 'One survey.\nA traceable chain.',
    intro: 'An exploded view of the proposed operational architecture. Each stage has a job; each output has a limit.',
    input: 'Survey imagery + navigation',
    output: 'Reviewable contacts + proposed search-completeness layer',
    stages: [
      {
        id: '01', name: 'Ingest & quality', output: 'Usable survey geometry',
        body: 'Read sonar and navigation, correct slant-to-ground geometry and flag poor-quality returns before interpreting the image.'
      },
      {
        id: '02', name: 'Tile & context', output: '640 px tiles',
        body: 'Prepare detector tiles and retain range, seabed and quality context so a crop does not lose its survey conditions.'
      },
      {
        id: '03', name: 'Detect', output: 'D-FINE-S proposals',
        body: 'Propose candidate contacts. A detector score is not yet a calibrated probability or a confirmed ghost net.'
      },
      {
        id: '04', name: 'Inspect evidence', output: 'Supporting observations',
        body: 'Inspect texture, lines, shadows and local context. The proposed net-aware checks do not reject a contact solely for lacking a shadow.'
      },
      {
        id: '05', name: 'Calibrate & qualify', output: 'Probability + claim level',
        body: 'Use dataset-specific calibration, check applicability and apply the label-free counting rule instead of a fixed FA/km² threshold.'
      },
      {
        id: '06', name: 'Assess the search', output: 'Proposed completeness layer',
        body: 'Combine survey conditions with a validated detection-probability model when one is available. This map remains design / illustrative until measured.'
      },
      {
        id: '07', name: 'Position', output: 'Contact location + limits',
        body: 'Associate the contact with navigation and record positioning limitations. No measured positioning uncertainty is supplied here.'
      },
      {
        id: '08', name: 'Plan & export', output: 'Inspectable handoff',
        body: 'Support contact review and revisit planning. Preserve supporting evidence, claim level and provenance in the handoff.'
      }
    ],
    footer: 'Architecture reference: supplied video summary, updated with the current project brief.'
  },
  completeness: {
    id: 'completeness',
    eyebrow: 'The operational difference / Where to look again',
    title: 'A covered map\nis not an “all clear”.',
    intro: 'Track lines describe where the instrument travelled. The proposed completeness layer describes how well a target could have been detected.',
    mapTitle: 'From apparent coverage to visible gaps',
    mapLabel: 'Illustrative search area with survey passes and weaker or unobserved areas. No geographic position or probability is assigned.',
    legend: ['Illustrated survey pass', 'Weaker search evidence', 'Unobserved gap'],
    notes: [
      {
        title: 'A contact probability is local.',
        body: 'It concerns a proposed finding. It does not say how thoroughly the surrounding seabed was searched.'
      },
      {
        title: 'Detection probability concerns the search.',
        body: 'The proposed Pd model depends on target and survey conditions. It needs real validation before a completeness claim can be made.'
      },
      {
        title: 'Make the next pass useful.',
        body: 'The design exposes gaps and weaker search evidence so an agency can discuss revisit priorities, rather than interpret an empty suspect list as clearance.'
      }
    ],
    footer: 'No measured Pd values, cell probabilities or geographic claims are shown.'
  },
  validation: {
    id: 'honest-test',
    eyebrow: 'The evidence / Research, not a deployment promise',
    title: 'Show the result.\nKeep the conditions.',
    intro: 'These are the supplied measured NetSight results. They do not validate the illustrative search-completeness map or establish field performance on ghost nets.',
    splitTitle: 'What the model has seen changes the result.',
    splitNote: 'Same-model comparison from the supplied research results. AP50 is a detection metric, not the probability that a particular contact is real.',
    resultsTitle: 'Target-specific performance',
    dataset: 'Dataset',
    target: 'Target / condition',
    metric: 'AP50',
    average: 'Reported average',
    compared: 'Previous research model',
    calibrationTitle: 'Calibration needs an applicability statement.',
    calibrationMetric: 'Reported calibration error',
    calibrationNote: 'The supplied results report the error range without specifying the error metric here. Do not read it as AP50 or a contact probability.',
    levelsTitle: 'What the claim level means',
    budgetTitle: 'Budget held on the tested new surveys',
    fixed: 'Fixed in advance',
    counting: 'Label-free counting rule',
    budgetNote: 'Observed on the supplied set of 12 new surveys. This is not a promise about the next survey, and the display does not imply paired survey identities.',
    learningTitle: 'Experience means recordings, not neighbouring crops.',
    learningMetric: 'Training recordings → crab-pot AP50',
    limitsTitle: 'What this does not establish',
    limits: [
      'The supplied target library includes crab pots and other sonar objects; those results are not a measured ghost-net benchmark.',
      'Synthetic net injection and the search-completeness map remain design / illustrative until measured.',
      'Calibration and applicability need checking on the intended survey data.'
    ]
  },
  contact: {
    id: 'handoff',
    eyebrow: 'The handoff / One contact, end to end',
    title: 'Follow the finding.\nNot a mysterious score.',
    intro: 'Contact #17 is a narrative example, not a real detection. It has no assigned probability, position, dimensions or dive rank.',
    label: 'Contact #17 · design / illustrative until measured',
    journey: [
      {
        title: 'Proposal',
        body: 'A candidate region enters review with its source tile and survey context. Detection alone does not identify confirmed gear.'
      },
      {
        title: 'Evidence',
        body: 'The reviewer inspects the return and supporting observations. In this proposed collapsed-net example, no shadow is required.'
      },
      {
        title: 'Claim',
        body: 'The handoff records probability only when supported, alongside calibrated, indicative or withdrawn applicability. This illustration assigns none.'
      },
      {
        title: 'Action',
        body: 'The agency can inspect the record and discuss a check or revisit. A proposed completeness layer adds search context, not proof of the contact.'
      }
    ],
    packTitle: 'What should travel with the finding',
    packIntro: 'The supplied implementation describes JSON, a report and a hash-chained ledger. This page shows the record structure, not a fabricated export.',
    pack: [
      'Source survey and contact reference',
      'Supporting observations',
      'Probability, where supported',
      'Applicability and claim level',
      'Location and positioning limitations',
      'JSON, report and ledger reference'
    ],
    ledgerNote: 'A tamper-evident ledger helps reveal record changes. It does not make the detection correct.',
    ledgerSource: 'Source: supplied NetSight content.ts · evidence pack / ledger.',
    matrixTitle: 'Requirements → architecture',
    matrixNote: 'Design traceability from the video summary, not a verified compliance assessment.',
    matrixHeaders: ['Operational need', 'Proposed stages', 'What the reviewer receives'],
    matrix: [
      ['Prepare survey data', '01–02', 'Geometry, quality and context'],
      ['Locate candidate contacts', '03–04', 'Detection and supporting observations'],
      ['Interpret confidence', '05', 'Calibration and applicability'],
      ['Identify weaker search', '06', 'Proposed search-completeness layer'],
      ['Locate and hand off', '07–08', 'Position context and inspectable exports']
    ]
  },
  next: {
    id: 'next',
    eyebrow: 'The next step / A useful pilot begins with data',
    title: 'Bring a survey.\nTest the limits.',
    intro: 'For SIH judges, funders and survey agencies: support a bounded evaluation, not an unsupported field-readiness claim.',
    measuredTitle: 'Measured now',
    measuredBody: 'Detection benchmarks, the calibration-error range and the tested counting-rule result are reported above from the supplied project content.',
    designTitle: 'Still to validate',
    designBody: 'Ghost-net performance, synthetic injection, spatial detection probability and the illustrative operational handoff need intended-use evidence.',
    requestTitle: 'What a pilot discussion needs',
    requests: [
      'An appropriately licensed, labelled survey sector, with real target confirmations where available.',
      'Sensor, geometry, navigation and quality information needed to interpret the data.',
      'Agreed evaluation splits and operational review criteria before reporting results.',
      'A dataset and dependency licensing review before reuse or redistribution.'
    ],
    dataNote: 'The video names candidate datasets and tools, but their licences are not established by this page. No public ghost-net dataset count or unverified dataset-size claim is repeated.',
    briefAction: 'Download the pilot discussion brief',
    reviewAction: 'Review the measured evidence',
    downloadName: 'netsight-pilot-discussion.txt',
    brief: [
      'NetSight — pilot discussion brief',
      '',
      'Purpose: discuss a bounded side-scan evaluation with a survey agency.',
      'Research results are summarised on the site from the supplied project content.',
      'The search-completeness map, synthetic net injection and contact #17 are design / illustrative until measured.',
      '',
      'Requested inputs:',
      '- An appropriately licensed labelled survey sector and target confirmations where available.',
      '- Sensor geometry, navigation and quality information.',
      '- Evaluation splits and operational review criteria agreed before reporting.',
      '- Dataset and dependency licensing review.',
      '',
      'Outputs to agree: target-specific detection results, calibration applicability, review burden and evidence needed for a spatial detection-probability study.',
      '',
      'This is a discussion brief, not a survey result, evidence export or deployment approval.'
    ].join('\n'),
    footer: 'NetSight · SIH26057 · Research project',
    top: 'Return to surface'
  }
} as const;
