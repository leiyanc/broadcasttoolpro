import fs from "node:fs/promises";
import path from "node:path";
import {
  SpreadsheetFile,
  Workbook,
} from "@oai/artifact-tool";


const outputPath = process.argv[2];
if (!outputPath) {
  throw new Error("Provide the output .xlsx path.");
}

const columns = [
  ["Channel (Optional)", "Channel name or ID.", "Text", "Comercio TV", "Optional"],
  ["Air Date", "Local broadcast date.", "Date: YYYY-MM-DD", "2026-07-18", "Required"],
  ["Start Time", "Local programme start time.", "Time", "8:00 AM", "Required"],
  ["Program Title", "Series or programme title.", "Text", "Morning News", "Required"],
  ["Duration (Conditional)", "Programme duration. Required on the final row.", "HH:MM:SS", "00:30:00", "Conditional"],
  ["Parental Rating", "TV or movie content rating.", "Dropdown / Text", "TV-PG", "Required"],
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

function addBrandHeader(sheet, title, subtitle, endColumn = "Z") {
  if (endColumn !== "B") {
    sheet.mergeCells(`B1:${endColumn}1`);
    sheet.mergeCells(`B2:${endColumn}2`);
  }
  sheet.getRange("A1:A2").merge();
  sheet.getRange("A1").values = [["B"]];
  sheet.getRange("A1").format = {
    fill: blue,
    font: { bold: true, color: white, size: 22 },
    horizontalAlignment: "center",
    verticalAlignment: "center",
  };
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
  sheet.getRange("A1:Z2").format.rowHeight = 25;
  sheet.getRange("A1").format.columnWidth = 7;
  sheet.showGridLines = false;
}

addBrandHeader(
  programming,
  "Broadcast Tool Pro - XMLTV Programming Template",
  "Enter one row per programme using the channel's local time zone.",
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
for (const range of ["Q5:S504", "Z5:Z504"]) {
  programming.getRange(range).dataValidation = {
    rule: { type: "list", values: ["Yes", "No"] },
  };
}
programming.getRange("F5:F504").dataValidation = {
  rule: {
    type: "list",
    values: ["TV-Y", "TV-Y7", "TV-G", "TV-PG", "TV-14", "TV-MA", "G", "PG", "PG-13", "R", "NR"],
  },
};
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
  "How to Use This Template",
  "Keep the worksheet name and column headers unchanged.",
  "C",
);
const steps = [
  ["Step", "Instruction"],
  [1, "Complete the Programming sheet using the channel's local schedule time."],
  [2, "Use one row for every programme or event."],
  [3, "Complete all required fields: Air Date, Start Time, Program Title, Description, Genre, and Parental Rating."],
  [4, "Enter either Episode Description or Program Description. Episode Description takes priority in XMLTV."],
  [5, "Asset ID is optional. Leave it blank to let Broadcast Tool Pro generate it automatically."],
  [6, "Use HH:MM:SS for Duration. The final programme must include a duration."],
  [7, "Use Yes or No for Premiere, Live, New, and Previously Shown."],
  [8, "Separate cast members and keywords with semicolons."],
  [9, "Save the workbook as .xlsx, upload it, and select the channel's IANA time zone."],
  [10, "Choose ISO 8601 for broad compatibility or XMLTV Compact when required by a platform."],
];
instructions.getRange(`A4:B${steps.length + 3}`).values = steps;
instructions.getRange("A4:B4").format = {
  fill: navy,
  font: { bold: true, color: white },
};
instructions.getRange(`A5:B${steps.length + 3}`).format = {
  fill: pale,
  borders: {
    insideHorizontal: { style: "thin", color: line },
  },
  wrapText: true,
  verticalAlignment: "top",
};
instructions.getRange("A:A").format.columnWidth = 10;
instructions.getRange("B:B").format.columnWidth = 95;
instructions.getRange("C:C").format.columnWidth = 2;
instructions.freezePanes.freezeRows(4);

addBrandHeader(
  reference,
  "XMLTV Field Reference",
  "Required fields are highlighted in blue; optional fields are shown in gray.",
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
    requirement === "Required" ? required : optional
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
  ["Instructions", "A1:C14"],
  ["Field Reference", "A1:E30"],
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
