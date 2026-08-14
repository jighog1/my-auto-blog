const KOREAN_CHARACTERS_PER_MINUTE = 500;
const LATIN_WORDS_PER_MINUTE = 220;

export default function getReadingTime(markdown = "") {
  const plainText = markdown
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/https?:\/\/\S+/g, " ")
    .replace(/[#>*_`\[\]()-]/g, " ");
  const koreanCharacters =
    plainText.match(/[\p{Script=Hangul}]/gu)?.length ?? 0;
  const latinWords = plainText.match(/[A-Za-z0-9]+/g)?.length ?? 0;
  const minutes =
    koreanCharacters / KOREAN_CHARACTERS_PER_MINUTE +
    latinWords / LATIN_WORDS_PER_MINUTE;

  return Math.max(1, Math.ceil(minutes));
}
