using System.ComponentModel;
using Newtonsoft.Json;

namespace DiscordBot.HypixelApi;

public class HypixelPlayerResponse {
    [JsonProperty("success")]
    [DefaultValue(false)]
    public bool Success { get; private set; }

    [JsonProperty("stats")] private PlayerStats _stats { get; set; }

    public PlayerStats Stats {
        get { return _stats ?? (_stats = new PlayerStats()); }
        private set { _stats = value; }
    }
}

public class PlayerStats {
    private BedwarsStats _bedwarsStats;

    [JsonProperty("bedwars")]
    public BedwarsStats BedwarsStats {
        get { return _bedwarsStats ?? (_bedwarsStats = new BedwarsStats()); }
        private set { _bedwarsStats = value; }
    }
}

public class BedwarsStats {
    [JsonProperty("wins_bedwars")] [DefaultValue(0)]
    public int Wins { get; private set; }
    
    
    [JsonProperty("eight_one_wins_bedwars")] [DefaultValue(0)]
    public int SolosWins { get; private set; }
    
    [JsonProperty("eight_two_wins_bedwars")] [DefaultValue(0)]
    public int DoublesWins { get; private set; }

}