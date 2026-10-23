"""🌟 The NBA star list COMPILED FROM CLAUDE'S OWN KNOWLEDGE (10/23 - the sandbox can't reach Wikipedia / Basketball-
Reference; the owner: "look at the squad - Jaylen Brown, Maxey, Edgecombe, Embiid, LeBron James ... the engine needs to
know that too"). All-Star selections (incl. injury replacements), All-NBA 1st / 2nd / 3rd teams, MVP top-5 and the
All-Rookie first team by the season's END year (2024 = the 2023-24 season), and the top-10 picks by draft year.

Every season here is marked source "claude-knowledge". The nba_stars workflow (tools/nba_stars_fetch.py, on GitHub's
servers) reads Basketball-Reference and REPLACES every season it can read (source "bbref") - 2026 is not in this file
at all: it comes from the fetch or not at all (never a fact we can't see).

    python tools/nba_stars_compiled.py data/sports/nba_stars.json
"""
import json
import sys

S = {}


def sea(y, all_nba, all_star, mvp, rook):
    S[str(y)] = {"all_nba": {"1": all_nba[0], "2": all_nba[1], "3": all_nba[2]}, "all_star": all_star,
                 "mvp_top5": mvp, "all_rookie_1": rook, "source": "claude-knowledge"}


sea(2014, [["Kevin Durant", "LeBron James", "Joakim Noah", "James Harden", "Chris Paul"],
           ["Blake Griffin", "Kevin Love", "Dwight Howard", "Stephen Curry", "Tony Parker"],
           ["Paul George", "LaMarcus Aldridge", "Al Jefferson", "Goran Dragic", "Damian Lillard"]],
    ["Kyrie Irving", "Dwyane Wade", "LeBron James", "Paul George", "Carmelo Anthony", "Chris Bosh", "DeMar DeRozan",
     "Roy Hibbert", "Joe Johnson", "Paul Millsap", "Joakim Noah", "John Wall", "Stephen Curry", "Kobe Bryant",
     "Kevin Durant", "Blake Griffin", "Kevin Love", "LaMarcus Aldridge", "Dwight Howard", "Damian Lillard",
     "Dirk Nowitzki", "Tony Parker", "Chris Paul", "James Harden", "Anthony Davis"],
    ["Kevin Durant", "LeBron James", "Blake Griffin", "Joakim Noah", "James Harden"],
    ["Michael Carter-Williams", "Victor Oladipo", "Trey Burke", "Tim Hardaway Jr.", "Mason Plumlee"])
sea(2015, [["LeBron James", "Anthony Davis", "Marc Gasol", "James Harden", "Stephen Curry"],
           ["LaMarcus Aldridge", "DeAndre Jordan", "Pau Gasol", "Chris Paul", "Russell Westbrook"],
           ["Blake Griffin", "Tim Duncan", "DeMarcus Cousins", "Klay Thompson", "Kyrie Irving"]],
    ["John Wall", "Kyle Lowry", "LeBron James", "Pau Gasol", "Carmelo Anthony", "Al Horford", "Kyrie Irving",
     "Jimmy Butler", "Jeff Teague", "Paul Millsap", "Chris Bosh", "Dwyane Wade", "Kyle Korver", "Stephen Curry",
     "Kobe Bryant", "Anthony Davis", "Blake Griffin", "Marc Gasol", "LaMarcus Aldridge", "Tim Duncan", "James Harden",
     "Damian Lillard", "Klay Thompson", "Russell Westbrook", "DeMarcus Cousins", "Dirk Nowitzki"],
    ["Stephen Curry", "James Harden", "LeBron James", "Russell Westbrook", "Anthony Davis"],
    ["Andrew Wiggins", "Nikola Mirotic", "Nerlens Noel", "Elfrid Payton", "Jordan Clarkson"])
sea(2016, [["LeBron James", "Kawhi Leonard", "DeAndre Jordan", "Stephen Curry", "Russell Westbrook"],
           ["Kevin Durant", "Draymond Green", "DeMarcus Cousins", "Chris Paul", "Damian Lillard"],
           ["Paul George", "LaMarcus Aldridge", "Andre Drummond", "Klay Thompson", "Kyle Lowry"]],
    ["Kyle Lowry", "Dwyane Wade", "LeBron James", "Paul George", "Carmelo Anthony", "Chris Bosh", "Jimmy Butler",
     "DeMar DeRozan", "Al Horford", "Paul Millsap", "Isaiah Thomas", "John Wall", "Pau Gasol", "Stephen Curry",
     "Russell Westbrook", "Kobe Bryant", "Kevin Durant", "Kawhi Leonard", "LaMarcus Aldridge", "DeMarcus Cousins",
     "Anthony Davis", "Draymond Green", "James Harden", "Chris Paul", "Klay Thompson"],
    ["Stephen Curry", "Kawhi Leonard", "LeBron James", "Russell Westbrook", "Kevin Durant"],
    ["Karl-Anthony Towns", "Kristaps Porzingis", "Devin Booker", "Jahlil Okafor", "Nikola Jokic"])
sea(2017, [["LeBron James", "Kawhi Leonard", "Anthony Davis", "James Harden", "Russell Westbrook"],
           ["Kevin Durant", "Giannis Antetokounmpo", "Rudy Gobert", "Stephen Curry", "Isaiah Thomas"],
           ["Draymond Green", "Jimmy Butler", "DeAndre Jordan", "John Wall", "DeMar DeRozan"]],
    ["Kyrie Irving", "DeMar DeRozan", "LeBron James", "Jimmy Butler", "Giannis Antetokounmpo", "Isaiah Thomas",
     "John Wall", "Kevin Love", "Paul George", "Kyle Lowry", "Paul Millsap", "Kemba Walker", "Carmelo Anthony",
     "Stephen Curry", "James Harden", "Kevin Durant", "Kawhi Leonard", "Anthony Davis", "Russell Westbrook",
     "Klay Thompson", "DeMarcus Cousins", "Marc Gasol", "DeAndre Jordan", "Gordon Hayward", "Draymond Green"],
    ["Russell Westbrook", "James Harden", "Kawhi Leonard", "LeBron James", "Isaiah Thomas"],
    ["Malcolm Brogdon", "Dario Saric", "Joel Embiid", "Buddy Hield", "Willy Hernangomez"])
sea(2018, [["LeBron James", "Kevin Durant", "Anthony Davis", "James Harden", "Damian Lillard"],
           ["Giannis Antetokounmpo", "LaMarcus Aldridge", "Joel Embiid", "DeMar DeRozan", "Russell Westbrook"],
           ["Paul George", "Jimmy Butler", "Karl-Anthony Towns", "Stephen Curry", "Victor Oladipo"]],
    ["LeBron James", "Stephen Curry", "Kevin Durant", "Giannis Antetokounmpo", "Anthony Davis", "Kyrie Irving",
     "James Harden", "DeMar DeRozan", "Joel Embiid", "LaMarcus Aldridge", "Bradley Beal", "Jimmy Butler",
     "Draymond Green", "Al Horford", "Kevin Love", "Damian Lillard", "Kyle Lowry", "Victor Oladipo", "Klay Thompson",
     "Russell Westbrook", "John Wall", "DeMarcus Cousins", "Kristaps Porzingis", "Paul George", "Andre Drummond",
     "Goran Dragic", "Karl-Anthony Towns"],
    ["James Harden", "LeBron James", "Anthony Davis", "Damian Lillard", "Giannis Antetokounmpo"],
    ["Ben Simmons", "Donovan Mitchell", "Jayson Tatum", "Kyle Kuzma", "Lauri Markkanen"])
sea(2019, [["Giannis Antetokounmpo", "Paul George", "Nikola Jokic", "James Harden", "Stephen Curry"],
           ["Kevin Durant", "Kawhi Leonard", "Joel Embiid", "Kyrie Irving", "Damian Lillard"],
           ["LeBron James", "Blake Griffin", "Rudy Gobert", "Russell Westbrook", "Kemba Walker"]],
    ["LeBron James", "Giannis Antetokounmpo", "Kevin Durant", "Kawhi Leonard", "James Harden", "Joel Embiid",
     "Paul George", "Kyrie Irving", "Kemba Walker", "Stephen Curry", "Damian Lillard", "Nikola Jokic",
     "Karl-Anthony Towns", "Klay Thompson", "Russell Westbrook", "LaMarcus Aldridge", "Anthony Davis", "Kyle Lowry",
     "Khris Middleton", "Blake Griffin", "Ben Simmons", "Nikola Vucevic", "Bradley Beal", "Victor Oladipo",
     "D'Angelo Russell", "Dirk Nowitzki", "Dwyane Wade"],
    ["Giannis Antetokounmpo", "James Harden", "Paul George", "Nikola Jokic", "Stephen Curry"],
    ["Luka Doncic", "Trae Young", "Deandre Ayton", "Jaren Jackson Jr.", "Marvin Bagley III"])
sea(2020, [["Giannis Antetokounmpo", "LeBron James", "Anthony Davis", "James Harden", "Luka Doncic"],
           ["Kawhi Leonard", "Pascal Siakam", "Nikola Jokic", "Damian Lillard", "Chris Paul"],
           ["Jimmy Butler", "Jayson Tatum", "Rudy Gobert", "Ben Simmons", "Russell Westbrook"]],
    ["Giannis Antetokounmpo", "LeBron James", "Kawhi Leonard", "Luka Doncic", "James Harden", "Joel Embiid",
     "Pascal Siakam", "Trae Young", "Kemba Walker", "Anthony Davis", "Damian Lillard", "Devin Booker", "Nikola Jokic",
     "Chris Paul", "Russell Westbrook", "Rudy Gobert", "Donovan Mitchell", "Brandon Ingram", "Jimmy Butler",
     "Jayson Tatum", "Khris Middleton", "Kyle Lowry", "Bam Adebayo", "Ben Simmons", "Domantas Sabonis"],
    ["Giannis Antetokounmpo", "LeBron James", "James Harden", "Luka Doncic", "Kawhi Leonard"],
    ["Ja Morant", "Kendrick Nunn", "Brandon Clarke", "Zion Williamson", "Eric Paschall"])
sea(2021, [["Giannis Antetokounmpo", "Kawhi Leonard", "Nikola Jokic", "Stephen Curry", "Luka Doncic"],
           ["LeBron James", "Julius Randle", "Joel Embiid", "Damian Lillard", "Chris Paul"],
           ["Jimmy Butler", "Paul George", "Rudy Gobert", "Bradley Beal", "Kyrie Irving"]],
    ["LeBron James", "Giannis Antetokounmpo", "Kevin Durant", "Kawhi Leonard", "Luka Doncic", "Stephen Curry",
     "Joel Embiid", "Kyrie Irving", "Bradley Beal", "Jaylen Brown", "Damian Lillard", "Chris Paul", "Nikola Jokic",
     "Paul George", "Zion Williamson", "Rudy Gobert", "Anthony Davis", "Jayson Tatum", "Ben Simmons", "James Harden",
     "Julius Randle", "Zach LaVine", "Nikola Vucevic", "Donovan Mitchell", "Devin Booker", "Mike Conley",
     "Domantas Sabonis"],
    ["Nikola Jokic", "Joel Embiid", "Stephen Curry", "Giannis Antetokounmpo", "Chris Paul"],
    ["LaMelo Ball", "Anthony Edwards", "Tyrese Haliburton", "Saddiq Bey", "Jae'Sean Tate"])
sea(2022, [["Giannis Antetokounmpo", "Jayson Tatum", "Nikola Jokic", "Luka Doncic", "Devin Booker"],
           ["Kevin Durant", "DeMar DeRozan", "Joel Embiid", "Ja Morant", "Stephen Curry"],
           ["LeBron James", "Pascal Siakam", "Karl-Anthony Towns", "Chris Paul", "Trae Young"]],
    ["LeBron James", "Giannis Antetokounmpo", "Kevin Durant", "Trae Young", "DeMar DeRozan", "Stephen Curry",
     "Nikola Jokic", "Ja Morant", "Andrew Wiggins", "Joel Embiid", "Luka Doncic", "Draymond Green", "Rudy Gobert",
     "Donovan Mitchell", "Chris Paul", "Devin Booker", "Karl-Anthony Towns", "Jimmy Butler", "Darius Garland",
     "Zach LaVine", "Jayson Tatum", "Khris Middleton", "Fred VanVleet", "James Harden", "LaMelo Ball",
     "Jarrett Allen", "Dejounte Murray"],
    ["Nikola Jokic", "Joel Embiid", "Giannis Antetokounmpo", "Devin Booker", "Luka Doncic"],
    ["Scottie Barnes", "Evan Mobley", "Cade Cunningham", "Franz Wagner", "Jalen Green"])
sea(2023, [["Giannis Antetokounmpo", "Jayson Tatum", "Joel Embiid", "Luka Doncic", "Shai Gilgeous-Alexander"],
           ["Jimmy Butler", "Jaylen Brown", "Nikola Jokic", "Damian Lillard", "Donovan Mitchell"],
           ["LeBron James", "Julius Randle", "Domantas Sabonis", "Stephen Curry", "De'Aaron Fox"]],
    ["Giannis Antetokounmpo", "Kevin Durant", "Jayson Tatum", "Kyrie Irving", "Donovan Mitchell", "LeBron James",
     "Nikola Jokic", "Zion Williamson", "Luka Doncic", "Stephen Curry", "Joel Embiid", "Jaylen Brown",
     "DeMar DeRozan", "Tyrese Haliburton", "Julius Randle", "Bam Adebayo", "Jrue Holiday", "Damian Lillard",
     "Ja Morant", "Shai Gilgeous-Alexander", "Lauri Markkanen", "Paul George", "Domantas Sabonis",
     "Jaren Jackson Jr.", "Pascal Siakam", "De'Aaron Fox", "Anthony Edwards"],
    ["Joel Embiid", "Nikola Jokic", "Giannis Antetokounmpo", "Jayson Tatum", "Shai Gilgeous-Alexander"],
    ["Paolo Banchero", "Walker Kessler", "Bennedict Mathurin", "Keegan Murray", "Jalen Williams"])
sea(2024, [["Giannis Antetokounmpo", "Luka Doncic", "Shai Gilgeous-Alexander", "Nikola Jokic", "Jayson Tatum"],
           ["Jalen Brunson", "Anthony Davis", "Kevin Durant", "Anthony Edwards", "Kawhi Leonard"],
           ["Devin Booker", "Stephen Curry", "LeBron James", "Tyrese Haliburton", "Domantas Sabonis"]],
    ["Giannis Antetokounmpo", "Joel Embiid", "Jayson Tatum", "Tyrese Haliburton", "Damian Lillard", "LeBron James",
     "Nikola Jokic", "Kevin Durant", "Luka Doncic", "Shai Gilgeous-Alexander", "Bam Adebayo", "Paolo Banchero",
     "Jalen Brunson", "Tyrese Maxey", "Donovan Mitchell", "Julius Randle", "Jaylen Brown", "Scottie Barnes",
     "Trae Young", "Devin Booker", "Anthony Davis", "Anthony Edwards", "Paul George", "Karl-Anthony Towns",
     "Kawhi Leonard", "Stephen Curry"],
    ["Nikola Jokic", "Shai Gilgeous-Alexander", "Luka Doncic", "Giannis Antetokounmpo", "Jalen Brunson"],
    ["Victor Wembanyama", "Chet Holmgren", "Brandon Miller", "Jaime Jaquez Jr.", "Brandin Podziemski"])
sea(2025, [["Shai Gilgeous-Alexander", "Nikola Jokic", "Giannis Antetokounmpo", "Jayson Tatum", "Donovan Mitchell"],
           ["Anthony Edwards", "Jalen Brunson", "LeBron James", "Evan Mobley", "Cade Cunningham"],
           ["Stephen Curry", "Jalen Williams", "Karl-Anthony Towns", "Tyrese Haliburton", "James Harden"]],
    ["Giannis Antetokounmpo", "Jayson Tatum", "Jalen Brunson", "Donovan Mitchell", "Karl-Anthony Towns",
     "LeBron James", "Nikola Jokic", "Kevin Durant", "Shai Gilgeous-Alexander", "Stephen Curry", "Darius Garland",
     "Tyler Herro", "Evan Mobley", "Pascal Siakam", "Trae Young", "Cade Cunningham", "Damian Lillard",
     "Anthony Davis", "Anthony Edwards", "James Harden", "Alperen Sengun", "Jalen Williams", "Victor Wembanyama",
     "Kyrie Irving"],
    ["Shai Gilgeous-Alexander", "Nikola Jokic", "Giannis Antetokounmpo", "Donovan Mitchell", "Cade Cunningham"],
    ["Stephon Castle", "Jaylen Wells", "Zaccharie Risacher", "Alex Sarr", "Zach Edey"])

DRAFT = {   # the top 10 in order, by draft year (a pick's rookie season starts that fall)
    "2013": ["Anthony Bennett", "Victor Oladipo", "Otto Porter Jr.", "Cody Zeller", "Alex Len", "Nerlens Noel",
             "Ben McLemore", "Kentavious Caldwell-Pope", "Trey Burke", "C.J. McCollum"],
    "2014": ["Andrew Wiggins", "Jabari Parker", "Joel Embiid", "Aaron Gordon", "Dante Exum", "Marcus Smart",
             "Julius Randle", "Nik Stauskas", "Noah Vonleh", "Elfrid Payton"],
    "2015": ["Karl-Anthony Towns", "D'Angelo Russell", "Jahlil Okafor", "Kristaps Porzingis", "Mario Hezonja",
             "Willie Cauley-Stein", "Emmanuel Mudiay", "Stanley Johnson", "Frank Kaminsky", "Justise Winslow"],
    "2016": ["Ben Simmons", "Brandon Ingram", "Jaylen Brown", "Dragan Bender", "Kris Dunn", "Buddy Hield",
             "Jamal Murray", "Marquese Chriss", "Jakob Poeltl", "Thon Maker"],
    "2017": ["Markelle Fultz", "Lonzo Ball", "Jayson Tatum", "Josh Jackson", "De'Aaron Fox", "Jonathan Isaac",
             "Lauri Markkanen", "Frank Ntilikina", "Dennis Smith Jr.", "Zach Collins"],
    "2018": ["Deandre Ayton", "Marvin Bagley III", "Luka Doncic", "Jaren Jackson Jr.", "Trae Young", "Mo Bamba",
             "Wendell Carter Jr.", "Collin Sexton", "Kevin Knox", "Mikal Bridges"],
    "2019": ["Zion Williamson", "Ja Morant", "RJ Barrett", "De'Andre Hunter", "Darius Garland", "Jarrett Culver",
             "Coby White", "Jaxson Hayes", "Rui Hachimura", "Cam Reddish"],
    "2020": ["Anthony Edwards", "James Wiseman", "LaMelo Ball", "Patrick Williams", "Isaac Okoro", "Onyeka Okongwu",
             "Killian Hayes", "Obi Toppin", "Deni Avdija", "Jalen Smith"],
    "2021": ["Cade Cunningham", "Jalen Green", "Evan Mobley", "Scottie Barnes", "Jalen Suggs", "Josh Giddey",
             "Jonathan Kuminga", "Franz Wagner", "Davion Mitchell", "Ziaire Williams"],
    "2022": ["Paolo Banchero", "Chet Holmgren", "Jabari Smith Jr.", "Keegan Murray", "Jaden Ivey",
             "Bennedict Mathurin", "Shaedon Sharpe", "Dyson Daniels", "Jeremy Sochan", "Johnny Davis"],
    "2023": ["Victor Wembanyama", "Brandon Miller", "Scoot Henderson", "Amen Thompson", "Ausar Thompson",
             "Anthony Black", "Bilal Coulibaly", "Jarace Walker", "Taylor Hendricks", "Cason Wallace"],
    "2024": ["Zaccharie Risacher", "Alex Sarr", "Reed Sheppard", "Stephon Castle", "Ron Holland II",
             "Tidjane Salaun", "Donovan Clingan", "Rob Dillingham", "Zach Edey", "Cody Williams"],
    "2025": ["Cooper Flagg", "Dylan Harper", "VJ Edgecombe", "Kon Knueppel", "Ace Bailey", "Tre Johnson",
             "Jeremiah Fears", "Egor Demin", "Collin Murray-Boyles", "Khaman Maluach"],
}


def build():
    return {"v": 1, "built": "2026-10-23",
            "note": "Seasons keyed by END year (2024 = 2023-24). Source 'claude-knowledge' = compiled from Claude's own "
                    "knowledge on 10/23 (All-Star selections incl. replacements, All-NBA 1st/2nd/3rd, MVP top-5, "
                    "All-Rookie first team; the top-10 picks by draft year). 2026 is NOT here: the nba_stars workflow "
                    "(tools/nba_stars_fetch.py) reads Basketball-Reference and replaces every season it can read "
                    "(source 'bbref').",
            "seasons": S, "draft": DRAFT}


if __name__ == "__main__":
    out = build()
    with open(sys.argv[1], "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(len(S), "seasons,", sum(len(v["all_star"]) for v in S.values()), "All-Star selections,",
          sum(len(v) for v in DRAFT.values()), "draft picks")
