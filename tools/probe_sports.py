"""Live price check, game by game: Bovada's live line vs Action Network's, and whether our game matches."""
import sys

sys.path.insert(0, ".")
import sports_data as sd  # noqa: E402
import sports_live as sl  # noqa: E402

games = sd.load_games()
for lg in ("nfl", "ncaaf"):
    books = sl.bovada_live(lg)
    print(f"\n{lg}: {len(books)} bovada live lines; errors {sd.ERRORS[-2:]}")
    for b in books[:4]:
        print("   bovada", b)
    for ang in sl.fetch_live(lg):
        box = ang.get("boxscore") or {}
        if not box.get("period") or str(ang.get("status") or "").lower() in sl.DONE:
            continue
        g = sl._match(games, lg, ang)
        an = sl.live_line(box)
        bk = sl.book_line(books, g) if g else (None, None)
        nv = lambda x: round(sd.no_vig(*x), 3) if x[0] is not None and x[1] is not None else None  # noqa: E731
        print(f"   {g['away_name'] + ' @ ' + g['home_name'] if g else 'NO MATCH ' + str(ang.get('id'))}: "
              f"bovada {bk} ({nv(bk)})  AN {an} ({nv(an)})  -> {sl.confirmed_line(bk, an)}")
