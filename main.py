import pandas as pd
import random
import sys
import collections
import json
import os
import glob
import matplotlib.pyplot as plt

SIMULATIONS = 100000

DRAW_RATES_FILE = "candidates_draw_rates.json"
PERFORMANCE_RATINGS_FILE = "candidates_performance_ratings.json"

WHITE_ELO_BONUS_CLASSICAL = 35
WHITE_ELO_BONUS_RAPID = 20
WHITE_ELO_BONUS_BLITZ = 10
PERFORMANCE_VARIANCE = 50

MIN_DRAW_PROB = 0.35
DRAW_FACTOR_RAPID = 0.7
DRAW_FACTOR_BLITZ = 0.5


def get_latest_ratings_file():
    files = glob.glob("current_player_ratings_*.json")
    if not files:
        return None
    files.sort()
    return files[-1]


def load_player_data():
    players = collections.defaultdict(dict)
    if not os.path.exists(DRAW_RATES_FILE):
        print(f"Error: '{DRAW_RATES_FILE}' not found. Run calculate_stats.py first.")
        sys.exit()
        
    with open(DRAW_RATES_FILE, "r") as f:
        draw_data_list = json.load(f)
        draw_lookup = {item["Name"]: item["Draw Rate"] for item in draw_data_list}

    latest_file = get_latest_ratings_file()
    
    if latest_file:
        print(f"Found most recent live ratings: {latest_file}")
        ratings_file = latest_file
    elif os.path.exists(PERFORMANCE_RATINGS_FILE):
        print(f"No current ratings found. Using: {PERFORMANCE_RATINGS_FILE}")
        ratings_file = PERFORMANCE_RATINGS_FILE
    else:
        print(f"Error: No ratings file found.")
        sys.exit()

    with open(ratings_file, "r") as f:
        ratings_data_list = json.load(f)

    for entry in ratings_data_list:
        name = entry["Name"]
        ratings = entry["Ratings"] 
        
        classical_draw_rate = draw_lookup.get(name, 0.55)
        
        c_rating = ratings.get("Classical")
        if c_rating is None:
             print(f"Warning: No Classical rating for {name}, skipping.")
             continue

        players[name]["Classical"] = {
            "Rating": float(c_rating),
            "Draw_Rate": classical_draw_rate
        }
        
        r_rating = ratings.get("Rapid")
        if r_rating is None: r_rating = c_rating
        
        players[name]["Rapid"] = {
            "Rating": float(r_rating),
            "Draw_Rate": classical_draw_rate * DRAW_FACTOR_RAPID
        }
        
        b_rating = ratings.get("Blitz")
        if b_rating is None: b_rating = c_rating
        
        players[name]["Blitz"] = {
            "Rating": float(b_rating),
            "Draw_Rate": classical_draw_rate * DRAW_FACTOR_BLITZ
        }

    return players, list(players.keys())

players, player_names = load_player_data()


def simulate_game(white, black, mode="Classical", w_rating_override=None, b_rating_override=None):

    if mode == "Classical": white_bonus = WHITE_ELO_BONUS_CLASSICAL
    elif mode == "Rapid": white_bonus = WHITE_ELO_BONUS_RAPID
    else: white_bonus = WHITE_ELO_BONUS_BLITZ

    p1_stats = players[white][mode]
    p2_stats = players[black][mode]
    
    r1 = w_rating_override if w_rating_override is not None else p1_stats["Rating"]
    r2 = b_rating_override if b_rating_override is not None else p2_stats["Rating"]

    eff_white_rating = r1 + white_bonus
    gap = eff_white_rating - r2
    expected_score = 1 / (1 + 10 ** (-gap / 400))
    
    base_draw = (p1_stats["Draw_Rate"] + p2_stats["Draw_Rate"]) / 2
    
    raw_draw_prob = base_draw * (1 - abs(2 * expected_score - 1))
    draw_prob = max(raw_draw_prob, MIN_DRAW_PROB)
    
    white_win_prob = expected_score - (draw_prob / 2)
    if white_win_prob < 0: white_win_prob = 0
    if white_win_prob + draw_prob > 1: draw_prob = 1 - white_win_prob
    
    r = random.random()
    if r < white_win_prob: return 1.0
    elif r < white_win_prob + draw_prob: return 0.5
    else: return 0.0


def play_match(p1, p2, mode, games=2):
    s1 = 0
    s2 = 0
    for i in range(games):
        if i % 2 == 0: 
            res = simulate_game(p1, p2, mode)
            s1 += res
            s2 += (1.0 - res)
        else:
            res = simulate_game(p2, p1, mode) 
            s2 += res
            s1 += (1.0 - res)
    return s1, s2


def play_round_robin(participants, mode):
    scores = {p: 0.0 for p in participants}
    n = len(participants)

    for i in range(n):
        for j in range(i + 1, n):
            p1, p2 = participants[i], participants[j]
            if random.random() > 0.5:
                res = simulate_game(p1, p2, mode)
                scores[p1] += res
                scores[p2] += (1 - res)
            else:
                res = simulate_game(p2, p1, mode)
                scores[p2] += res
                scores[p1] += (1 - res)
                
    max_score = max(scores.values())
    return [p for p, s in scores.items() if s == max_score]


def resolve_stage_1(participants):
    count = len(participants)
    if count == 2:
        s1, s2 = play_match(participants[0], participants[1], "Rapid", games=2)
        if s1 > s2: return [participants[0]]
        if s2 > s1: return [participants[1]]
        return participants
    elif 3 <= count <= 6:
        return play_round_robin(participants, "Rapid")
    else:
        return play_round_robin(participants, "Rapid")


def resolve_stage_2(participants):
    if len(participants) == 2:
        s1, s2 = play_match(participants[0], participants[1], "Blitz", games=2)
        if s1 > s2: return [participants[0]]
        if s2 > s1: return [participants[1]]
        return participants
    else:
        return play_round_robin(participants, "Blitz")


def play_sudden_death_match(p1, p2):
    if random.random() > 0.5:
        white, black = p1, p2
    else:
        white, black = p2, p1

    while True:
        res = simulate_game(white, black, "Blitz")
        if res == 1.0: return white
        if res == 0.0: return black
        white, black = black, white


def resolve_stage_3(participants):
    random.shuffle(participants)
    while len(participants) > 1:
        next_round = []
        i = 0
        while i < len(participants):
            p1 = participants[i]
            if i + 1 < len(participants):
                p2 = participants[i+1]
                winner = play_sudden_death_match(p1, p2)
                next_round.append(winner)
                i += 2
            else:
                next_round.append(p1)
                i += 1
        participants = next_round
    return participants[0]


def resolve_full_tiebreak(tied_players):
    survivors = resolve_stage_1(tied_players)
    if len(survivors) == 1: return survivors[0]
    
    survivors = resolve_stage_2(survivors)
    if len(survivors) == 1: return survivors[0]
    
    return resolve_stage_3(survivors)


print(f"Simulating {SIMULATIONS} tournaments...")
wins = {name: 0 for name in player_names}
tie_stats = {"count": 0, "winners": collections.defaultdict(int)}

schedule = []
for i in range(len(player_names)):
    for j in range(i + 1, len(player_names)):
        schedule.append((player_names[i], player_names[j]))
        schedule.append((player_names[j], player_names[i]))

for sim in range(SIMULATIONS):
    scores = {name: 0.0 for name in player_names}
    
    sim_ratings = {}
    for name in player_names:
        base_rating = players[name]["Classical"]["Rating"]
        form = random.gauss(0, PERFORMANCE_VARIANCE)
        sim_ratings[name] = base_rating + form

    for white, black in schedule:
        w_r = sim_ratings[white]
        b_r = sim_ratings[black]
        
        res = simulate_game(white, black, "Classical", w_rating_override=w_r, b_rating_override=b_r)
        
        scores[white] += res
        scores[black] += (1.0 - res)
        
    max_score = max(scores.values())
    tied_for_first = [p for p, s in scores.items() if s == max_score]
    
    if len(tied_for_first) == 1:
        wins[tied_for_first[0]] += 1
    else:
        tie_stats["count"] += 1
        winner = resolve_full_tiebreak(tied_for_first)
        wins[winner] += 1
        tie_stats["winners"][winner] += 1


def plot_results(player_names, wins, tie_stats, simulations):
    data = []
    for p in player_names:
        total_wins = wins[p]
        tb_wins = tie_stats["winners"][p]
        classical_wins = total_wins - tb_wins
        
        data.append({
            "name": p,
            "total_pct": (total_wins / simulations) * 100,
            "classical_pct": (classical_wins / simulations) * 100,
            "tb_pct": (tb_wins / simulations) * 100
        })
    
    data.sort(key=lambda x: x["total_pct"], reverse=True)
    names = [x["name"] for x in data]
    classical_pcts = [x["classical_pct"] for x in data]
    tb_pcts = [x["tb_pct"] for x in data]

    plt.figure(figsize=(10, 6))
    plt.bar(names, classical_pcts, label='Classical Win', color='#2C3E50')
    plt.bar(names, tb_pcts, bottom=classical_pcts, label='Tie-Break Win', color='#E67E22')

    plt.title(f"Candidates 2026 Win Probabilities (N={simulations})", fontsize=14, pad=20)
    plt.ylabel("Win Probability (%)", fontsize=12)
    plt.xlabel("Candidate", fontsize=12)
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    for i, (c, t) in enumerate(zip(classical_pcts, tb_pcts)):
        total = c + t
        if total > 0:
            plt.text(i, total + 0.5, f"{total:.1f}%", ha='center', fontsize=10, fontweight='bold')

    plt.tight_layout()
    plt.savefig("candidates_forecast.png", dpi=300)
    print("\nChart saved as 'candidates_forecast.png'")


def plot_results_table(player_names, wins, tie_stats, simulations):
    data = []
    for p in player_names:
        total_wins = wins[p]
        tb_wins = tie_stats["winners"][p]
        classical_wins = total_wins - tb_wins
        
        data.append({
            "name": p,
            "total_pct": (total_wins / simulations) * 100,
            "classical_pct": (classical_wins / simulations) * 100,
            "tb_pct": (tb_wins / simulations) * 100
        })
    
    data.sort(key=lambda x: x["total_pct"], reverse=True)
    table_data = []

    for i, row in enumerate(data, 1):
        table_data.append([
            f"{i}",
            row["name"],
            f"{row['total_pct']:.1f}%",
            f"{row['classical_pct']:.1f}%",
            f"{row['tb_pct']:.1f}%"
        ])

    fig, ax = plt.subplots(figsize=(8, len(data) * 0.5 + 1))
    ax.axis('off')

    col_labels = ["Rank", "Candidate", "Total Win %", "Classical %", "Tie-Break %"]
    table = ax.table(cellText=table_data, colLabels=col_labels, loc='center', cellLoc='center')

    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 1.5)

    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold', color='white')
            cell.set_facecolor('#4e79a7')
            cell.set_linewidth(0)
        else:
            cell.set_linewidth(0)
            if row % 2 == 0:
                cell.set_facecolor('#f2f2f2')
    
    plt.title(f"Candidates 2026 Forecast (N={simulations})", weight='bold', pad=10)
    plt.savefig("candidates_results_table.png", bbox_inches='tight', dpi=300)
    print("Table saved as 'candidates_results_table.png'")


print("\n===== CANDIDATES 2026 SIMULATION =====")

results = []
for name in player_names:
    win_pct = (wins[name] / SIMULATIONS) * 100
    tb_pct = (tie_stats["winners"][name] / SIMULATIONS) * 100
    results.append((name, win_pct, tb_pct))

results.sort(key=lambda x: x[1], reverse=True)

for i, (name, pct, tb) in enumerate(results, 1):
    classical_pct = pct - tb
    print(f"{i}. {name}: {pct:.1f}%")
    if pct > 0:
        print(f"   (Classical: {classical_pct:.1f}% | Tie-Break: {tb:.1f}%)")
    print()

print(f"Total Tie-Breaks: {tie_stats['count']} out of {SIMULATIONS} simulations ({tie_stats['count']/SIMULATIONS*100:.1f}%)")

plot_results(player_names, wins, tie_stats, SIMULATIONS)
plot_results_table(player_names, wins, tie_stats, SIMULATIONS)


