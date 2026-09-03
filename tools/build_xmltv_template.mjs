import fs from "node:fs/promises";
import path from "node:path";
import {
  SpreadsheetFile,
  Workbook,
} from "@oai/artifact-tool";


const outputPath = process.argv[2];
const brandMarkPath = process.argv[3];
if (!outputPath || !brandMarkPath) {
  throw new Error("Provide the output .xlsx path and brand mark PNG path.");
}
const brandMarkData = await fs.readFile(brandMarkPath);
const brandMarkDataUrl = `data:image/png;base64,${brandMarkData.toString("base64")}`;

const columns = [
  ["Channel", "EN: Exact registered channel name; it must match every row. ES: Nombre exacto del canal registrado; debe coincidir en cada fila.", "Exact text / Texto exacto", "Comercio TV", "Required / Obligatorio"],
  ["Air Date", "Local broadcast date.", "Date: YYYY-MM-DD", "2026-07-18", "Required"],
  ["Start Time", "Local programme start time.", "Time", "8:00 AM", "Required"],
  ["Program Title", "Series or programme title.", "Text", "Morning News", "Required"],
  ["Duration (Conditional)", "Programme duration. Required on the final row.", "HH:MM:SS", "00:30:00", "Conditional"],
  ["Parental Rating (Optional)", "EN: Optional rating interpreted using the channel's Rating System. Enter the official value, then copy or drag it across programmes when appropriate. ES: Clasificación opcional interpretada con el Rating System del canal. Escribe el valor oficial y cópialo o arrástralo cuando corresponda.", "Free text / Texto libre", "TV-PG", "Optional / Opcional"],
  ["Program Description (Conditional)", "Programme-level synopsis; fallback when episode description is blank.", "Text", "Daily morning news.", "Conditional"],
  ["Original Title (Optional)", "Title in the original language.", "Text", "Noticias Matutinas", "Optional"],
  ["Cast (Optional)", "Cast names separated by semicolons.", "Text", "Jane Doe; John Smith", "Optional"],
  ["Season Number (Optional)", "Season number for episodic content.", "Whole number", "1", "Optional"],
  ["Episode Number (Optional)", "Episode number for episodic content.", "Whole number", "1", "Optional"],
  ["Original Episode Title (Optional)", "Episode title.", "Text", "Opening Edition", "Optional"],
  ["Episode Description (Conditional)", "Episode synopsis; preferred XMLTV description.", "Text", "The day's top stories.", "Conditional"],
  ["Genre", "Genre or category.", "Text", "News", "Required"],
  ["Country of Production (Optional)", "Country where the content was produced.", "Text", "United States", "Optional"],
  ["Production Year (Optional)", "Production year for internal metadata.", "YYYY", "2026", "Optional"],
  ["Premiere (Optional)", "Indicates a premiere.", "Yes / No", "Yes", "Optional"],
  ["Live (Optional)", "Indicates this specific airing is live.", "Yes / No", "Yes", "Optional"],
  ["New (Optional)", "Indicates a new episode or programme.", "Yes / No", "Yes", "Optional"],
  ["Asset ID (Optional)", "Unique video asset identifier. Generated automatically when blank.", "Text", "morning-news-s01e01", "Optional"],
  ["Original Air Date (Optional)", "Original release or air date.", "Date: YYYY-MM-DD", "2026-07-18", "Optional"],
  ["Icon URL (Optional)", "Public programme or episode image URL.", "HTTPS URL", "https://example.com/image.jpg", "Optional"],
  ["Icon Width (Optional)", "Image width in pixels.", "Whole number", "1920", "Optional"],
  ["Icon Height (Optional)", "Image height in pixels.", "Whole number", "1080", "Optional"],
  ["Keywords (Optional)", "Keywords separated by semicolons.", "Text", "news; morning", "Optional"],
  ["Previously Shown (Optional)", "Indicates a repeat or previously aired programme.", "Yes / No", "No", "Optional"],
];

const headers = columns.map((column) => column[0]);
const languageOptions = [
  ["English (en)", "en", "General / General"],
  ["Español (es)", "es", "General / General"],
  ["Français (fr)", "fr", "General / General"],
  ["Português (pt)", "pt", "General / General"],
  ["中文 (zh)", "zh", "General / General"],
  ["English — United States (en-US)", "en-US", "Americas / Américas"],
  ["English — Canada (en-CA)", "en-CA", "Americas / Américas"],
  ["Français — Canada (fr-CA)", "fr-CA", "Americas / Américas"],
  ["Español — México (es-MX)", "es-MX", "Americas / Américas"],
  ["Español — Latinoamérica (es-419)", "es-419", "Americas / Américas"],
  ["Português — Brasil (pt-BR)", "pt-BR", "Americas / Américas"],
  ["Kreyòl ayisyen (ht)", "ht", "Americas / Américas"],
  ["English — United Kingdom (en-GB)", "en-GB", "Europe / Europa"],
  ["Español — España (es-ES)", "es-ES", "Europe / Europa"],
  ["Français — France (fr-FR)", "fr-FR", "Europe / Europa"],
  ["Deutsch (de)", "de", "Europe / Europa"],
  ["Italiano (it)", "it", "Europe / Europa"],
  ["Português — Portugal (pt-PT)", "pt-PT", "Europe / Europa"],
  ["Nederlands (nl)", "nl", "Europe / Europa"],
  ["Polski (pl)", "pl", "Europe / Europa"],
  ["Русский (ru)", "ru", "Europe / Europa"],
  ["Українська (uk)", "uk", "Europe / Europa"],
  ["中文 — 简体 (zh-Hans)", "zh-Hans", "Asia / Asia"],
  ["中文 — 繁體 (zh-Hant)", "zh-Hant", "Asia / Asia"],
  ["中文 — 中国 (zh-CN)", "zh-CN", "Asia / Asia"],
  ["中文 — 台灣 (zh-TW)", "zh-TW", "Asia / Asia"],
  ["中文 — 香港 (zh-HK)", "zh-HK", "Asia / Asia"],
  ["日本語 (ja)", "ja", "Asia / Asia"],
  ["한국어 (ko)", "ko", "Asia / Asia"],
  ["हिन्दी (hi)", "hi", "Asia / Asia"],
  ["বাংলা (bn)", "bn", "Asia / Asia"],
  ["Bahasa Indonesia (id)", "id", "Asia / Asia"],
  ["Bahasa Melayu (ms)", "ms", "Asia / Asia"],
  ["ไทย (th)", "th", "Asia / Asia"],
  ["Tiếng Việt (vi)", "vi", "Asia / Asia"],
  ["Filipino (fil)", "fil", "Asia / Asia"],
  ["العربية (ar)", "ar", "Middle East / Medio Oriente"],
  ["עברית (he)", "he", "Middle East / Medio Oriente"],
  ["فارسی (fa)", "fa", "Middle East / Medio Oriente"],
  ["Türkçe (tr)", "tr", "Middle East / Medio Oriente"],
  ["اردو (ur)", "ur", "Middle East / Medio Oriente"],
  ["Kiswahili (sw)", "sw", "Africa / África"],
  ["አማርኛ (am)", "am", "Africa / África"],
  ["Hausa (ha)", "ha", "Africa / África"],
  ["Yorùbá (yo)", "yo", "Africa / África"],
  ["isiZulu (zu)", "zu", "Africa / África"],
  ["Afrikaans (af)", "af", "Africa / África"],
  ["English — Australia (en-AU)", "en-AU", "Oceania / Oceanía"],
  ["English — New Zealand (en-NZ)", "en-NZ", "Oceania / Oceanía"],
  ["Te reo Māori (mi)", "mi", "Oceania / Oceanía"],
  ["Vosa Vakaviti (fj)", "fj", "Oceania / Oceanía"],
  ["Gagana Sāmoa (sm)", "sm", "Oceania / Oceanía"],
  ["Lea faka-Tonga (to)", "to", "Oceania / Oceanía"],
];
const ratingSystemOptions = [
  ["VCHIP — TV Parental Guidelines", "VCHIP", "United States / Estados Unidos"],
  ["MPA — Motion Picture Association", "MPA", "United States / Estados Unidos"],
  ["BBFC — British Board of Film Classification", "BBFC", "United Kingdom / Reino Unido"],
  ["FSK — Freiwillige Selbstkontrolle", "FSK", "Germany / Alemania"],
  ["DJCTQ — Classificação Indicativa", "DJCTQ", "Brazil / Brasil"],
  ["ACB — Australian Classification Board", "ACB", "Australia / Australia"],
  ["CBFC — Central Board of Film Certification", "CBFC", "India / India"],
  ["CNC — Classification cinématographique", "CNC", "France / Francia"],
  ["ICAA — Calificación por edades", "ICAA", "Spain / España"],
  ["KMRB — Korea Media Rating Board", "KMRB", "South Korea / Corea del Sur"],
  ["EIRIN — Film Classification and Rating", "EIRIN", "Japan / Japón"],
  ["MTRCB — Movie and Television Review", "MTRCB", "Philippines / Filipinas"],
  ["FPB — Film and Publication Board", "FPB", "South Africa / Sudáfrica"],
  ["CERO — Computer Entertainment Rating", "CERO", "Japan / Japón"],
  ["OFLC-NZ — Office of Film and Literature Classification", "OFLC-NZ", "New Zealand / Nueva Zelanda"],
  ["IMDA — Infocomm Media Development Authority", "IMDA", "Singapore / Singapur"],
];
const workbook = Workbook.create();
const programming = workbook.worksheets.add("Programming");
const instructions = workbook.worksheets.add("Instructions");
const reference = workbook.worksheets.add("Field Reference");
const example = workbook.worksheets.add("Example");

const navy = "#102A43";
const blue = "#2563EB";
const lightBlue = "#EAF2FF";
const pale = "#F7FAFC";
const line = "#D7E1EC";
const white = "#FFFFFF";
const required = "#DBEAFE";
const optional = "#EEF2F7";

function addBrandHeader(sheet, title, subtitle, endColumn = "AB") {
  if (endColumn !== "B") {
    sheet.mergeCells(`B1:${endColumn}1`);
    sheet.mergeCells(`B2:${endColumn}2`);
  }
  sheet.getRange("A1:A2").merge();
  sheet.getRange("A1").values = [[""]];
  sheet.getRange("A1").format = {
    fill: white,
    horizontalAlignment: "center",
    verticalAlignment: "center",
  };
  sheet.images.add({
    dataUrl: brandMarkDataUrl,
    anchor: {
      from: { row: 0, col: 0, rowOffsetPx: 3, colOffsetPx: 6 },
      extent: { widthPx: 44, heightPx: 41 },
    },
  });
  sheet.getRange("B1").values = [[title]];
  sheet.getRange("B1").format = {
    fill: navy,
    font: { bold: true, color: white, size: 16 },
    verticalAlignment: "center",
  };
  sheet.getRange("B2").values = [[subtitle]];
  sheet.getRange("B2").format = {
    fill: lightBlue,
    font: { color: navy, italic: true, size: 10 },
    verticalAlignment: "center",
  };
  sheet.getRange(`A1:${endColumn}2`).format.rowHeight = 25;
  sheet.getRange("A1").format.columnWidth = 7;
  sheet.showGridLines = false;
}

addBrandHeader(
  programming,
  "Broadcast Tool Pro - XMLTV Programming Template",
  "Enter one row per programme using the channel's local time zone.",
  "Z",
);
programming.getRange("A4:Z4").values = [headers];
programming.getRange("A4:Z4").format = {
  fill: navy,
  font: { bold: true, color: white, size: 9 },
  wrapText: true,
  verticalAlignment: "center",
  borders: { preset: "all", style: "thin", color: line },
};
programming.getRange("A4:Z4").format.rowHeight = 44;
programming.mergeCells("A3:Z3");
programming.getRange("A3").values = [[
  "Channel must match exactly / Channel debe coincidir exactamente · Parental Rating is optional free text / Parental Rating es texto libre opcional.",
]];
programming.getRange("A3").format = {
  fill: lightBlue,
  font: { color: navy, italic: true, size: 9 },
  verticalAlignment: "center",
};
programming.getRange("A3:Z3").format.rowHeight = 22;
programming.getRange("A5:Z504").format = {
  borders: {
    insideHorizontal: { style: "thin", color: line },
  },
  font: { size: 10 },
  verticalAlignment: "center",
};
programming.getRange("B5:B504").format.numberFormat = "yyyy-mm-dd";
programming.getRange("C5:C504").format.numberFormat = "h:mm AM/PM";
programming.getRange("E5:E504").format.numberFormat = "hh:mm:ss";
programming.getRange("U5:U504").format.numberFormat = "yyyy-mm-dd";
for (const range of ["B5:B504", "U5:U504"]) {
  programming.getRange(range).dataValidation = {
    rule: {
      type: "date",
      operator: "between",
      formula1: 36526,
      formula2: 73415,
    },
  };
}
for (const range of ["Q5:S504", "Z5:Z504"]) {
  programming.getRange(range).dataValidation = {
    rule: { type: "list", values: ["Yes", "No"] },
  };
}
programming.freezePanes.freezeRows(4);
programming.getRange("A4:Z504").format.columnWidth = 18;
for (const range of ["D:D", "G:I", "L:O", "T:T", "V:V", "Y:Y"]) {
  programming.getRange(range).format.columnWidth = 24;
}
for (const range of ["B:C", "E:F", "J:K", "P:U", "W:X", "Z:Z"]) {
  programming.getRange(range).format.columnWidth = 15;
}

addBrandHeader(
  instructions,
  "How to Use This Template / Cómo usar esta plantilla",
  "Keep worksheet names and headers unchanged. / No cambies los nombres de las hojas ni los encabezados.",
  "C",
);
const steps = [
  ["Step", "English", "Español"],
  [1, "Complete Programming using the channel's local schedule time.", "Completa Programming usando la hora local del canal."],
  [2, "Use one row for every programme or event.", "Usa una fila por cada programa o evento."],
  [3, "Channel is required and must exactly match the selected registered channel on every row.", "Channel es obligatorio y debe coincidir exactamente con el canal registrado seleccionado en cada fila."],
  [4, "Complete Air Date, Start Time, Program Title, a description, and Genre.", "Completa Air Date, Start Time, Program Title, una descripción y Genre."],
  [5, "Enter either Episode Description or Program Description. Episode Description takes priority.", "Ingresa Episode Description o Program Description. Episode Description tiene prioridad."],
  [6, "Use HH:MM:SS for Duration. The final programme must include a duration.", "Usa HH:MM:SS para Duration. El último programa debe incluir duración."],
  [7, "Use Yes or No for Premiere, Live, New, and Previously Shown.", "Usa Yes o No para Premiere, Live, New y Previously Shown."],
  [8, "Separate cast members and keywords with semicolons.", "Separa integrantes del elenco y palabras clave con punto y coma."],
  [9, "The registered channel's Primary Language and optional Rating System are applied automatically to XMLTV.", "El Primary Language y el Rating System opcional del canal registrado se aplican automáticamente al XMLTV."],
  [10, "Parental Rating is optional free text. Enter the official value used by the channel's configured Rating System.", "Parental Rating es texto libre opcional. Escribe el valor oficial utilizado por el Rating System configurado para el canal."],
  [11, "To reuse a rating, copy, paste, or drag the cell across the applicable programme rows. Do not select ratings from a dropdown.", "Para reutilizar una clasificación, copia, pega o arrastra la celda en las filas correspondientes. No selecciones clasificaciones de un menú."],
  [12, "Asset ID is optional; leave it blank for automatic generation.", "Asset ID es opcional; déjalo vacío para generarlo automáticamente."],
];
const stepsStartRow = 4;
const stepsEndRow = stepsStartRow + steps.length - 1;
instructions.getRange(`A${stepsStartRow}:C${stepsEndRow}`).values = steps;
instructions.getRange(`A${stepsStartRow}:C${stepsStartRow}`).format = {
  fill: navy,
  font: { bold: true, color: white },
};
instructions.getRange(`A${stepsStartRow + 1}:C${stepsEndRow}`).format = {
  fill: pale,
  borders: {
    insideHorizontal: { style: "thin", color: line },
  },
  wrapText: true,
  verticalAlignment: "top",
};
instructions.getRange("A:A").format.columnWidth = 10;
instructions.getRange("B:C").format.columnWidth = 52;
instructions.freezePanes.freezeRows(stepsStartRow);
const ratingGuideStart = stepsEndRow + 2;
const ratingGuide = [
  ["Rating System / Sistema", "Common values / Valores comunes", "How to enter / Cómo escribir"],
  ["VCHIP", "TV-Y · TV-Y7 · TV-G · TV-PG · TV-14 · TV-MA", "Enter TV-PG, not PG. / Escribe TV-PG, no PG."],
  ["MPA", "G · PG · PG-13 · R · NC-17", "Enter the official value exactly. / Escribe exactamente el valor oficial."],
  ["BBFC", "U · PG · 12A · 12 · 15 · 18 · R18", "Use the classification supplied for the programme. / Usa la clasificación suministrada para el programa."],
  ["FSK", "FSK 0 · FSK 6 · FSK 12 · FSK 16 · FSK 18", "The FSK prefix may be included. / Se puede incluir el prefijo FSK."],
  ["DJCTQ", "L · 10 · 12 · 14 · 16 · 18", "Use L for free classification. / Usa L para clasificación libre."],
  ["ACB", "G · PG · M · MA15+ · R18+ · X18+", "Copy or drag repeated values. / Copia o arrastra los valores repetidos."],
];
const ratingGuideEnd = ratingGuideStart + ratingGuide.length - 1;
instructions.getRange(`A${ratingGuideStart}:C${ratingGuideEnd}`).values = ratingGuide;
instructions.getRange(`A${ratingGuideStart}:C${ratingGuideStart}`).format = {
  fill: navy,
  font: { bold: true, color: white },
  wrapText: true,
};
instructions.getRange(`A${ratingGuideStart + 1}:C${ratingGuideEnd}`).format = {
  fill: lightBlue,
  borders: { insideHorizontal: { style: "thin", color: line } },
  wrapText: true,
  verticalAlignment: "top",
};

addBrandHeader(
  reference,
  "XMLTV Field Reference / Referencia de campos XMLTV",
  "Required / Obligatorio: blue · Optional / Opcional: gray",
  "E",
);
reference.getRange(`A4:E${columns.length + 4}`).values = [
  ["Column", "Description", "Expected Format", "Example", "Requirement"],
  ...columns,
];
reference.getRange("A4:E4").format = {
  fill: navy,
  font: { bold: true, color: white },
};
reference.getRange(`A5:E${columns.length + 4}`).format = {
  borders: {
    insideHorizontal: { style: "thin", color: line },
  },
  wrapText: true,
  verticalAlignment: "top",
};
for (let row = 5; row <= columns.length + 4; row += 1) {
  const requirement = columns[row - 5][4];
  reference.getRange(`A${row}:E${row}`).format.fill = (
    requirement.startsWith("Required") ? required : optional
  );
}
reference.getRange("A:A").format.columnWidth = 28;
reference.getRange("B:B").format.columnWidth = 52;
reference.getRange("C:C").format.columnWidth = 24;
reference.getRange("D:D").format.columnWidth = 34;
reference.getRange("E:E").format.columnWidth = 16;
reference.freezePanes.freezeRows(4);

addBrandHeader(
  example,
  "Completed Example - Do Not Upload This Sheet",
  "Copy the field patterns, then enter your real schedule on Programming.",
  "Z",
);
example.getRange("A4:Z4").values = [headers];
example.getRange("A4:Z4").format = {
  fill: navy,
  font: { bold: true, color: white, size: 9 },
  wrapText: true,
  verticalAlignment: "center",
  borders: { preset: "all", style: "thin", color: line },
};
example.getRange("A5:Z6").values = [
  [
    "Comercio TV", new Date("2026-07-18T00:00:00"), 8 / 24,
    "Morning News", 30 / 1440, "TV-PG", "Daily morning news.", "Noticias Matutinas",
    "Jane Doe; John Smith", 1, 1, "Opening Edition", "The day's top stories.",
    "News", "United States", 2026, "Yes", "Yes", "Yes", "morning-news-s01e01",
    new Date("2026-07-18T00:00:00"), "https://example.com/morning-news.jpg", 1920, 1080,
    "news; morning", "No",
  ],
  [
    "Comercio TV", new Date("2026-07-18T00:00:00"), 8.5 / 24,
    "Market Update", 30 / 1440, "TV-G", "Financial markets and analysis.", "Actualizacion del Mercado",
    "John Smith", 2, 14, "Opening Bell", "Market opening coverage.",
    "Business", "United States", 2026, "No", "Yes", "Yes", "market-update-s02e14",
    new Date("2026-07-18T00:00:00"), "", null, null, "business; markets", "No",
  ],
];
example.getRange("B5:B6").format.numberFormat = "yyyy-mm-dd";
example.getRange("C5:C6").format.numberFormat = "h:mm AM/PM";
example.getRange("E5:E6").format.numberFormat = "hh:mm:ss";
example.getRange("U5:U6").format.numberFormat = "yyyy-mm-dd";
example.getRange("A5:Z6").format = {
  fill: pale,
  borders: { preset: "all", style: "thin", color: line },
  font: { size: 9 },
  wrapText: true,
  verticalAlignment: "top",
};
example.getRange("A4:Z6").format.columnWidth = 18;
for (const range of ["D:D", "G:I", "L:O", "T:T", "V:V", "Y:Y"]) {
  example.getRange(range).format.columnWidth = 24;
}
example.freezePanes.freezeRows(4);

const outputDir = path.dirname(outputPath);
await fs.mkdir(outputDir, { recursive: true });
for (const [sheetName, range] of [
  ["Programming", "A1:Z14"],
  ["Instructions", `A1:C${ratingGuideEnd}`],
  ["Field Reference", `A1:E${columns.length + 4}`],
  ["Example", "A1:Z6"],
]) {
  const preview = await workbook.render({
    sheetName,
    range,
    scale: 1,
    format: "png",
  });
  await fs.writeFile(
    path.join(outputDir, `${sheetName.replaceAll(" ", "-")}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
}
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
