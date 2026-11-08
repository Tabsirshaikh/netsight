/**
 * Editorial source of truth, including Part B's data.
 * Scores are AP50 unless explicitly identified as calibration errors.
 * Illustration coordinates, animation timings and geometry are not measurements.
 */
export const content = {
  brand: 'NetSight',
  team: 'SIH26057',
  ui: {
    skip: 'Skip to the story',
    navLabel: 'Main navigation',
    home: 'NetSight home',
    mission: 'The mission',
    system: 'The system',
    validation: 'The honest test',
    scroll: 'Scroll to descend',
    scrollHint: 'A scroll-driven field guide',
    soundOff: 'Sound off',
    soundOn: 'Sound on',
    soundLabel: 'Toggle a quiet, synthesised sonar illustration',
    depthLabel: 'Story progress, from surface to seabed',
    surface: '0 m',
    bottom: 'Seabed',
    illustration: 'Procedural illustration · not a survey',
    research: 'Research model',
    ap50: 'AP50',
    chapter: 'Chapter',
    placeholder: 'Next in the story',
    placeholderNote: 'This chapter is reserved for the next build. Its research notes are available below.',
    expandNotes: 'Read the research notes',
    back: 'Back to the story',
    pending: 'Phase 1 · dashboard preview',
    dashboardTitle: 'The next view is the evidence.',
    dashboardBody: 'The dashboard is a placeholder in this phase. The research workflow will connect survey ingestion, detections, claim levels and downloadable evidence.',
    dashboardItems: ['Survey workspace', 'Detection review', 'Claim-level explanation', 'Evidence export'],
    dashboardStatus: 'Interface forthcoming · no survey uploaded',
    sceneLoading: 'Preparing the procedural illustration',
    canvasFallback: 'A simplified procedural illustration is shown because 3D rendering is unavailable.'
  },
  s01: {
    id: 'mission',
    eyebrow: 'Seabed intelligence / research project',
    title: 'NetSight',
    subtitle: 'Finds debris in side-scan sonar — and tells you how far to trust each find.',
    statement: 'Beneath the surface.\nBeyond the score.',
    targets: 'Ghost fishing nets · traps · lost gear · wrecks',
    vessel: 'Research vessel',
    towfish: 'Side-scan towfish',
    surfaceLabel: '01 / Above the surface',
    diveLabel: '02 / Read the seabed',
    signal: 'Acoustic pings, not photographs.',
    description: 'A research vessel pulls a side-scan towfish. As the view descends, sideways acoustic pings reveal the seabed below.',
    next: 'First, learn to see with sound.'
  },
  s02: {
    id: 'side-scan',
    eyebrow: '01 / The instrument',
    title: 'An image made\nof echoes.',
    intro: 'A towfish sends acoustic pings sideways. Each returning echo paints another line of a seabed image.',
    phases: [
      { name: 'Send', text: 'A ping spreads to either side of the towfish.' },
      { name: 'Listen', text: 'Objects return stronger echoes and cast acoustic shadows.' },
      { name: 'Build', text: 'Returns accumulate, line by line, into a waterfall image.' }
    ],
    net: 'Net + acoustic shadow',
    trap: 'Trap + acoustic shadow',
    nadir: 'Nadir / water-column gap',
    nadirExplanation: 'Directly below the towfish, the water-column gap stays dark.',
    port: 'Port return',
    starboard: 'Starboard return',
    line: 'One return → one image line',
    description: 'A procedural side-scan image builds from top to bottom. A net and trap have bright returns beside darker acoustic shadows. The central dark strip is the nadir.',
    footer: 'Brightness is an echo. Darkness can be evidence, too.'
  },
  s03: {
    id: 'system',
    eyebrow: '02 / The system',
    title: 'Not just a box.\nA chain of evidence.',
    intro: 'One survey enters. Six connected operations explain what comes out.',
    description: 'Six procedural instrument layers separate into an exploded view, light up in sequence, and reassemble into one system.',
    assembly: 'One connected system',
    steps: [
      { name: 'Normalise', short: 'One pixel geometry', text: 'Ingest the survey and convert every sonar to one pixel size.' },
      { name: 'Detect', short: 'D-FINE transformer', text: 'D-FINE, a transformer object detector, proposes debris locations.' },
      { name: 'Evidence', short: 'Look beyond the box', text: 'Inspect shadow and height, mesh texture, lines, ripple-pattern breaks and local anomaly.' },
      { name: 'Calibrate', short: 'Scores → probabilities', text: 'Turn overconfident detector scores into honest probabilities.' },
      { name: 'Gate', short: 'Check applicability', text: 'Ask whether this survey resembles validated data; choose calibrated, indicative or withdrawn.' },
      { name: 'Evidence pack', short: 'JSON + report + ledger', text: 'Export JSON and a report, recorded in a hash-chained, tamper-evident ledger.' }
    ],
    footer: 'A detection is the beginning of a claim. Not the end.'
  },
  s04: {
    id: 'honest-test',
    eyebrow: '03 / The honest test',
    title: 'Same model.\nDifferent reality.',
    intro: 'A result only means something when you know what the model has already seen.',
    columns: [
      { value: 0.72, title: 'Its own training images', caption: 'Tested on images used to train the model.', label: 'Seen before', tone: 'muted' },
      { value: 0.53, title: 'Random held-out images', caption: 'Different images, randomly held out.', label: 'Random split', tone: 'muted' },
      { value: 0.21, title: 'Never-seen survey years', caption: 'Survey years the model has never seen.', label: 'The deployment question', tone: 'accent' }
    ],
    context: 'Papers report 75–99% on random splits. NetSight reports performance on surveys the model has never seen.',
    punchline: 'A buyer needs the third number.',
    response: 'We report it.',
    description: 'Three columns compare the same model: 0.72 AP50 on its training images, 0.53 on random held-out images and 0.21 on never-seen survey years.',
    note: 'Test design changes the claim.',
    metric: 'Research model / AP50 · higher is better'
  },
  s05: {
    id: 'detections',
    eyebrow: '04 / Target library',
    title: 'What the model finds.',
    intro: 'Research model v0.4, evaluated on never-seen surveys.',
    results: [
      { dataset: 'SCTD', target: 'Shipwrecks / aircraft / people', value: 0.82 },
      { dataset: 'AquaScan', target: 'People', value: 0.61 },
      { dataset: 'GhostVision', target: 'Crab pots', value: 0.36 },
      { dataset: 'Contact', target: 'Different sensor', value: 0.26, specialist: 0.40 },
      { dataset: 'Mine-like objects', target: 'Mine-like objects', value: 0.22 }
    ],
    average: 0.42,
    previousAverage: 0.27,
    specialist: 'On Contact, the ghost-gear specialist lifts AP50 from 0.26 to 0.40.',
    summary: 'Average AP50: 0.42 for research model v0.4, compared with 0.27 for v0.1.',
    notes: [
      'SCTD: shipwrecks, aircraft and people — 0.82 AP50.',
      'AquaScan: people — 0.61 AP50.',
      'GhostVision: crab pots — 0.36 AP50.',
      'Contact: a different sensor — 0.26 AP50, rising to 0.40 with the ghost-gear specialist.',
      'Mine-like objects — 0.22 AP50.',
      'Research model v0.4 averages 0.42 AP50; v0.1 averaged 0.27.'
    ]
  },
  s06: {
    id: 'trust',
    eyebrow: '05 / The trust layer',
    title: 'Confidence needs conditions.',
    intro: 'A score is not a promise. Check the probability, the survey and the false-alarm budget.',
    levels: [
      { name: 'calibrated', text: 'The survey is within the applicability of the validated calibration.' },
      { name: 'indicative', text: 'Treat the output as an indication, not a calibrated probability.' },
      { name: 'withdrawn', text: 'The applicability gate withholds the claim.' }
    ],
    calibrationError: [0.004, 0.035],
    budget: { surveys: 12, fixedHeld: 4, fixedBroke: 8, labelFreeHeld: 12 },
    calibration: 'Raw detector scores are overconfident. After calibration, error is 0.004–0.035.',
    budgetText: 'A false-alarm budget fixed in advance broke on 8 of 12 new surveys. NetSight’s label-free counting rule held the budget on 12 of 12.',
    comparison: 'Budget held: 12 / 12 versus 4 / 12.',
    notes: [
      'Raw detector scores are overconfident; calibration reduces error to 0.004–0.035.',
      'The applicability gate selects calibrated, indicative or withdrawn according to the survey’s relationship to validated data.',
      'A fixed false-alarm budget broke on 8 of 12 new surveys.',
      'The label-free counting rule held that budget on 12 of 12.'
    ]
  },
  s07: {
    id: 'geometry',
    eyebrow: '06 / Pixel geometry',
    title: 'Fix the geometry.\nKeep the model.',
    intro: 'Correcting a survey’s pixel geometry lifted a stretched-sensor recording without retraining.',
    before: 0.175,
    after: 0.368,
    beforeLabel: 'Stretched recording',
    afterLabel: 'Corrected geometry',
    notes: ['Correcting pixel geometry lifted AP50 from 0.175 to 0.368 on a stretched-sensor recording, with no retraining.']
  },
  s08: {
    id: 'learning',
    eyebrow: '07 / More surveys',
    title: 'Learn across recordings.\nNot just images.',
    intro: 'More training surveys help the research model generalise.',
    points: [
      { recordings: 5, value: 0.26 },
      { recordings: 10, value: 0.34 },
      { recordings: 21, value: 0.37 }
    ],
    sensor: 'An unseen sensor tripled.',
    notes: [
      'Crab-pot detection rose from 0.26 to 0.34 to 0.37 AP50 with 5, 10 and 21 training recordings.',
      'Performance on an unseen sensor tripled.'
    ]
  },
  s09: {
    id: 'ledger',
    eyebrow: '08 / The evidence pack',
    title: 'A finding you can follow.',
    intro: 'JSON and a report preserve the evidence. A hash-chained ledger makes changes evident.',
    fields: ['Detection', 'Supporting evidence', 'Calibrated probability', 'Applicability / claim level', 'JSON + report', 'Ledger link'],
    valid: 'Chain intact',
    tampered: 'Change detected at this link',
    disclaimer: 'The ledger is tamper-evident; it does not make a detection correct.',
    notes: [
      'The evidence pack contains JSON and a report.',
      'Records are linked in a hash-chained, tamper-evident ledger.',
      'Changing one block breaks its relationship to the next link.',
      'A tamper-evident record preserves the claim; it does not prove the detection.'
    ]
  },
  s10: {
    id: 'next',
    eyebrow: '09 / From signal to evidence',
    title: 'See the find.\nKnow its limits.',
    intro: 'From a seabed echo to a claim you can inspect.',
    action: 'Open the dashboard',
    actionNote: 'Phase 1 / placeholder workspace',
    teamLabel: 'Built by team',
    signature: 'Beneath the surface. Beyond the score.',
    footer: 'NetSight · Research project',
    top: 'Return to surface',
    description: 'Six linked pieces of evidence converge around a sonar target, connecting detection to an inspectable record.'
  }
} as const;
