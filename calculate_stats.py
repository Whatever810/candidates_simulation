import pandas as pd
import json
import os
import matplotlib.pyplot as plt

def calculate_stats_2600(csv_path, fide_map_path="fide_table.json", rapid_blitz_path="rpd_blz_avg.json"):
    if not os.path.exists(fide_map_path):
        print(f"Error: '{fide_map_path}' not found.")
        return None
    with open(fide_map_path, "r") as f:
        fide_map = json.load(f)

    rapid_blitz_data = {}
    if os.path.exists(rapid_blitz_path):
        try:
            with open(rapid_blitz_path, "r") as f:
                rapid_blitz_data = json.load(f)

            if isinstance(rapid_blitz_data, list):
                pass 
        except Exception as e:
            print(f"Warning: Could not read '{rapid_blitz_path}'. {e}")

    if not os.path.exists(csv_path):
        print(f"File '{csv_path}' not found.")
        return None

    df = pd.read_csv(csv_path)

    df['Score'] = df['Score'].astype(str).replace({'½': '0.5', '1/2': '0.5'}).astype(float)
    df['Opponent Rating'] = pd.to_numeric(df['Opponent Rating'], errors='coerce')
    df = df.dropna(subset=['Opponent Rating'])
    df = df[df['Opponent Rating'] >= 2600]
    
    full_stats_list = []
    performance_ratings_list = []
    draw_rates_list = []

    candidates = df['Candidate'].unique()

    for player in candidates:
        player_games = df[df['Candidate'] == player]
        total_games = len(player_games)
        
        if total_games == 0:
            continue
            
        total_score = player_games['Score'].sum()
        avg_opp = player_games['Opponent Rating'].mean()
        score_pct = total_score / total_games
        
        pct_key = "{:.2f}".format(score_pct)
        if score_pct > 0.995: pct_key = "1.00"
        if score_pct < 0.005: pct_key = "0.00"
        
        dp = fide_map.get(pct_key, 0)
        tpr_classical = int(round(avg_opp + dp))
        
        draws = len(player_games[player_games['Score'] == 0.5])
        draw_rate = (draws / total_games)
        
        full_stats_list.append({
            "Name": player,
            "Games": total_games,
            "Score": total_score,
            "Avg Opp Rating": round(avg_opp, 1),
            "TPR": tpr_classical,
            "Draw Rate %": round(draw_rate * 100, 1)
        })

        p_rb = rapid_blitz_data.get(player, {})
        if isinstance(rapid_blitz_data, list):
             for p_obj in rapid_blitz_data:
                 if p_obj.get("Name") == player:
                     p_rb = p_obj.get("Ratings", {})
                     break

        rapid_rating = p_rb.get("Rapid", None)
        blitz_rating = p_rb.get("Blitz", None)

        performance_ratings_list.append({
            "Name": player,
            "Ratings": {
                "Classical": tpr_classical, 
                "Rapid": rapid_rating,      
                "Blitz": blitz_rating       
            }
        })

        draw_rates_list.append({
            "Name": player,
            "Draw Rate": round(draw_rate, 3)
        })
    
    summary_df = pd.DataFrame(full_stats_list)
    if not summary_df.empty:
        summary_df = summary_df.sort_values(by="TPR", ascending=False)
        print(f"\nClassical Performance Table (>2600)")
        print(summary_df.to_string(index=False))

    with open("candidates_performance_ratings.json", "w") as f:
        json.dump(performance_ratings_list, f, indent=4)
    print(f"Saved: candidates_performance_ratings.json")

    with open("candidates_draw_rates.json", "w") as f:
        json.dump(draw_rates_list, f, indent=4)
    print(f"Saved: candidates_draw_rates.json")

    if not summary_df.empty:
        generate_image_table(summary_df)


def generate_image_table(df):
    display_df = df.rename(columns={"Name": "Player"})
    
    fig, ax = plt.subplots(figsize=(10, len(display_df) * 0.5 + 1.5))
    ax.axis('off')
    ax.axis('tight')

    table = ax.table(cellText=display_df.values,
                     colLabels=display_df.columns,
                     loc='center',
                     cellLoc='center')

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.5)

    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor('#4e79a7')
            cell.set_text_props(weight='bold', color='white')
            cell.set_linewidth(0)
        else:
            cell.set_linewidth(0)
            if row % 2 == 0:
                cell.set_facecolor('#f2f2f2')

    plt.title("Classical Performance (>2600 Opponents)", weight='bold', pad=20)
    plt.savefig("stats_classical_table.png", bbox_inches='tight', dpi=300)
    print(f"Saved Image to stats_classical_table.png")
    plt.close()

if __name__ == "__main__":
    calculate_stats_2600("candidates_classical_2024_2026.csv")
