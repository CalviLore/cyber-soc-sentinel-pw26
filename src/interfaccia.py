"""Aspetto della chat: banner, riga di stato, input con cronologia e spinner.

Solo grafica: niente di quello che sta qui decide cosa fa l'agente. Se rich o
prompt_toolkit mancano, la chat funziona lo stesso in modo semplice (input()
e nessuno spinner).
"""
import sys
from pathlib import Path

try:
    from rich.console import Console
    from rich.text import Text
    RICH = True
except ImportError:  # pragma: no cover
    RICH = False

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.formatted_text import ANSI
    from prompt_toolkit.history import FileHistory
    PROMPT_TOOLKIT = True
except ImportError:  # pragma: no cover
    PROMPT_TOOLKIT = False

from modelli import coloreModello

VERSIONE = "1.0"
COMANDI = ["/models", "/nuova", "/help", "esci"]
AZZURRO = "#3b9ae1"

# Lettere del banner (font "standard" di figlet): ogni lettera e' fatta di 5 righe.
_LETTERE = {
    "S": [" ____  ", "/ ___| ", "\\___ \\ ", " ___) |", "|____/ "],
    "O": ["  ___  ", " / _ \\ ", "| | | |", "| |_| |", " \\___/ "],
    "C": ["  ____ ", " / ___|", "| |    ", "| |___ ", " \\____|"],
    "E": [" _____ ", "| ____|", "|  _|  ", "| |___ ", "|_____|"],
    "N": [" _   _ ", "| \\ | |", "|  \\| |", "| |\\  |", "|_| \\_|"],
    "T": [" _____ ", "|_   _|", "  | |  ", "  | |  ", "  |_|  "],
    "I": [" ___ ", "|_ _|", " | | ", " | | ", "|___|"],
    "L": [" _     ", "| |    ", "| |    ", "| |___ ", "|_____|"],
    " ": ["  ", "  ", "  ", "  ", "  "],
}


def testoBanner(parole="SOC SENTINEL"):
    """Il nome in lettere grandi, una stringa per riga."""
    return ["".join(_LETTERE[c][r] for c in parole) for r in range(5)]


def _console():
    return Console(highlight=False) if RICH else None


def mostraBanner(modello, provider, db, log):
    """Banner, riga di stato (modello, database, log) e suggerimento sui comandi."""
    console = _console()
    righe = testoBanner()
    if not console:
        print("\n".join(righe))
        print(f"modello: {modello}\nlog: {log}")
        print("Scrivi 'esci' per chiudere, '/nuova' per azzerare la memoria.")
        return
    console.print()
    for riga in righe:
        console.print(Text(riga, style=f"bold {AZZURRO}"))
    console.print(Text(f"  Agente SOC con server MCP · v{VERSIONE}", style="dim"))
    console.print()
    console.print(Text("  modello  ", style="dim")
                  + Text(str(modello), style=coloreModello(modello) or ""))
    console.print(Text("  provider ", style="dim") + Text(str(provider)))
    console.print(Text("  database ", style="dim") + Text(str(db)))
    console.print(Text("  log      ", style="dim") + Text(str(log)))
    console.print()
    console.print(Text("  Scrivi la richiesta e premi invio. ", style="dim")
                  + Text("/help", style=AZZURRO) + Text(" per i comandi.", style="dim"))
    console.print(Text("  " + "─" * 70, style="dim"))
    console.print()


def mostraHelp():
    console = _console()
    voci = [("/models", "scegli un altro modello (la conversazione continua)"),
            ("/nuova", "azzera la memoria e ricomincia da capo"),
            ("/help", "mostra questo elenco"),
            ("esci", "chiude la sessione (anche Ctrl+C)"),
            ("freccia su", "richiama le richieste precedenti"),
            ("Tab", "completa i comandi")]
    for comando, testo in voci:
        if console:
            console.print(Text(f"  {comando:<11}", style=AZZURRO) + Text(testo, style="dim"))
        else:
            print(f"  {comando:<11}{testo}")


def creaInput(fileCronologia):
    """Restituisce una funzione leggi() che chiede una riga all'operatore.

    Con prompt_toolkit: cronologia con la freccia su (salvata su file) e
    completamento dei comandi con Tab. Senza terminale vero (pipe, test) o senza
    la libreria si usa input()."""
    if not PROMPT_TOOLKIT or not sys.stdin.isatty():
        async def semplice():
            return input(">>> ")
        return semplice
    Path(fileCronologia).parent.mkdir(parents=True, exist_ok=True)
    sessione = PromptSession(
        history=FileHistory(str(fileCronologia)),
        completer=WordCompleter(COMANDI, sentence=True),
        complete_while_typing=False)
    async def leggi():
        return await sessione.prompt_async(ANSI("\033[1;94m>>>\033[0m "))
    return leggi


class Attesa:
    """Spinner "sto pensando..." mentre il modello lavora.

    Va fermato prima di una domanda all'operatore (la conferma Y/N) e fatto
    ripartire dopo: con conferma() si avvolge il callback di conferma."""

    def __init__(self, testo="Sto pensando…"):
        console = _console()
        self._status = (console.status(Text(testo, style="dim"), spinner="dots")
                        if console and sys.stdout.isatty() else None)
        self._attivo = False

    def avvia(self):
        if self._status and not self._attivo:
            self._status.start()
            self._attivo = True

    def ferma(self):
        if self._status and self._attivo:
            self._status.stop()
            self._attivo = False

    def conferma(self, ask):
        """Callback di conferma che ferma lo spinner mentre l'operatore risponde."""
        def avvolta(domanda):
            riprendi = self._attivo
            self.ferma()
            try:
                return ask(domanda)
            finally:
                if riprendi:
                    self.avvia()
        return avvolta
