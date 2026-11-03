/** Sentence-level caption timing follows measured narration length within each chapter. */
export function renderCaptions(chapters) {
  function timestamp(seconds) {
    const ms = Math.round(seconds * 1000);
    return `${String(Math.floor(ms / 3600000)).padStart(2, "0")}:${String(Math.floor(ms / 60000) % 60).padStart(2, "0")}:${String(Math.floor(ms / 1000) % 60).padStart(2, "0")},${String(ms % 1000).padStart(3, "0")}`;
  }
  const cues = [];
  for (const chapter of chapters) {
    const sentences = chapter.text.split(/(?<=[.!?])\s+/);
    const words = chapter.text.split(/\s+/).length;
    let elapsed = 0;
    for (const sentence of sentences) {
      const duration = chapter.narration_seconds * sentence.split(/\s+/).length / words;
      const lines = [];
      for (const word of sentence.split(/\s+/)) {
        if (!lines.length || lines.at(-1).length + word.length > 64) lines.push(word);
        else lines[lines.length - 1] += ` ${word}`;
      }
      cues.push(`${cues.length + 1}\n${timestamp(chapter.start + elapsed)} --> ${timestamp(chapter.start + elapsed + duration)}\n${lines.join("\n")}\n`);
      elapsed += duration;
    }
  }
  return cues.join("\n");
}
