from __future__ import annotations

import json
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path
from typing import Literal, TypedDict

import aiofiles

from webtoon_downloader.core.webtoon.models import ChapterInfo

TextExporterFormat = Literal["text", "json", "all"]


class ExportChapterData(TypedDict):
    """
    Typed dictionary representing the data structure for a single chapter in an export operation.

    Attributes:
        title   : The title of the chapter.
        notes   : Additional notes or text associated with the chapter.
    """

    title: str
    notes: str


class ExportData(TypedDict):
    """
    Typed dictionary representing the overall data structure for the export operation.

    Attributes:
        chapters    : A dictionary mapping chapter numbers to their respective data.
        summary     : A summary or overall text for the series being exported.
    """

    chapters: dict[int, ExportChapterData]
    summary: str


@dataclass
class TextExporter:
    """
    Writes text elements to files, either to multiple plain text files or/and to a single JSON file.

    Attributes:
        dest            : The destination directory for the exported files.
        export_format   : The format to export the data ('text', 'json', or 'all').
    """

    export_format: TextExporterFormat
    dest: str | PathLike[str] = field(default_factory=lambda: Path("."))

    _dest: Path = field(init=False)
    _data: ExportData = field(init=False)
    _write_json: bool = field(init=False)
    _write_text: bool = field(init=False)

    def __post_init__(self) -> None:
        self._data = {"chapters": {}, "summary": ""}
        self._dest = Path(self.dest)
        self._write_json = self.export_format in ["json", "all"]
        self._write_text = self.export_format in ["text", "all"]

    async def add_series_texts(self, summary: str | None, directory: str | PathLike[str] | None = None) -> None:
        """
        Adds the series summary to the export data.

        Args:
            summary     : The summary text of the series.
            directory   : The directory where the summary file will be written. Defaults to the main destination directory.
        """
        if not summary or not self._write_text:
            return

        self._data["summary"] = summary
        directory = Path(directory) if directory else self._dest
        await self._aio_write(directory / "summary.txt", summary)

    async def add_chapter_details(
        self,
        chapter: ChapterInfo,
        notes: str,
        padding: int = 0,
        directory: str | PathLike[str] | None = None,
    ) -> None:
        """
        Adds chapter texts to the export data.

        Args:
            chapter     : The chapter info object.
            notes       : Notes or additional text associated with the chapter.
            padding     : 0 padding to add to generated file.
            directory   : The directory where the chapter files will be written. Defaults to the main destination directory.
        """
        self._data["chapters"][chapter.number] = {"title": chapter.title, "notes": notes}

        if not self._write_text:
            return

        directory = Path(directory) if directory else self._dest
        await self._aio_write(directory / f"{chapter.number:0{padding}d}_title.txt", chapter.title)

        if notes:
            await self._aio_write(directory / f"{chapter.number:0{padding}d}_notes.txt", notes)

    async def write_data(
        self,
        directory: str | PathLike[str] | None = None,
    ) -> None:
        """
        Writes the collected data to a JSON file if JSON export is enabled.

        Args:
            directory: The directory where the JSON file will be written. Defaults to the main destination directory.
        """
        if not self._write_json:
            return

        directory = Path(directory) if directory else self._dest
        data = json.dumps(self._data, sort_keys=True, indent=4)
        await self._aio_write(directory / "info.json", data, end="")

    async def _aio_write(
        self,
        target: str | Path,
        data: str,
        mode: Literal["a", "w"] = "w",
        end: str = "\n",
    ) -> None:
        """
        Asynchronously writes the given data to a file, creating the parent path if it does not exist.

        Args:
            target  : The target file path where data will be written.
            data    : The data to be written to the file.
            mode    : The file opening mode ('a' for append, 'w' for write).
            end     : The string to append at the end of the file, typically a newline character.
        """
        target = Path(target)
        target.parent.mkdir(exist_ok=True, parents=True)
        async with aiofiles.open(target, mode=mode) as f:
            await f.write(data + end)
