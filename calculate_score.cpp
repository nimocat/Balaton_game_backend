#include <iostream>
#include <vector>
#include <algorithm>
#include <unordered_map>
#include <string>
#include <set>

using namespace std;

vector<string> suits = {"H", "S", "D", "C"};
vector<string> ranks = {"2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"};
vector<string> jokers = {"BJ", "RJ"};

int rank_index(const string& rank) {
    for (int i = 0; i < ranks.size(); ++i) {
        if (ranks[i] == rank) {
            return i;
        }
    }
    return -1;
}

bool is_flush(const vector<string>& hand) {
    char suit = hand[0][0];
    for (const string& card : hand) {
        if (card[0] != suit && card != "BJ" && card != "RJ") {
            return false;
        }
    }
    return true;
}

bool is_straight(const vector<int>& rank_indices) {
    for (int i = 0; i < rank_indices.size() - 1; ++i) {
        if (rank_indices[i + 1] - rank_indices[i] != 1) {
            return false;
        }
    }
    return true;
}

bool is_straight_flush(const vector<string>& hand) {
    vector<int> rank_indices;
    for (const string& card : hand) {
        if (card != "BJ" && card != "RJ") {
            rank_indices.push_back(rank_index(card.substr(1)));
        }
    }
    sort(rank_indices.begin(), rank_indices.end());
    return is_straight(rank_indices) && is_flush(hand);
}

bool is_royal_flush(const vector<string>& hand) {
    if (!is_straight_flush(hand)) {
        return false;
    }

    int num_jokers = count(hand.begin(), hand.end(), "BJ") + count(hand.begin(), hand.end(), "RJ");
    int num_high_cards = 0;

    for (const string& card : hand) {
        if (card[1] == 'T' || card[1] == 'J' || card[1] == 'Q' || card[1] == 'K' || card[1] == 'A') {
            ++num_high_cards;
        }
    }

    return num_high_cards + num_jokers >= 5;
}

pair<unordered_map<string, int>, int> get_rank_counts(const vector<string>& hand) {
    unordered_map<string, int> rank_counts;
    int joker_count = 0;
    for (const string& card : hand) {
        if (card == "BJ" || card == "RJ") {
            ++joker_count;
        } else {
            ++rank_counts[card.substr(1)];
        }
    }
    return make_pair(rank_counts, joker_count);
}

vector<string> replace_jokers(const vector<string>& hand, const string& replacement) {
    vector<string> new_hand;
    for (const string& card : hand) {
        if (card == "BJ" || card == "RJ") {
            new_hand.push_back(replacement);
        } else {
            new_hand.push_back(card);
        }
    }
    return new_hand;
}

int calculate_score_without_joker(const unordered_map<string, int>& rank_counts, const vector<string>& hand) {
    if (is_royal_flush(hand)) {
        return 20;
    }
    if (is_straight_flush(hand)) {
        return 15;
    }
    if (any_of(rank_counts.begin(), rank_counts.end(), [](const pair<string, int>& p) { return p.second == 4; })) {
        return 12;
    }
    vector<int> counts;
    for (const auto& p : rank_counts) {
        counts.push_back(p.second);
    }
    sort(counts.begin(), counts.end());
    if (counts.size() >= 2 && counts[counts.size() - 2] == 2 && counts[counts.size() - 1] == 3) {
        return 9;
    }
    if (is_flush(hand)) {
        return 7;
    }
    vector<int> rank_indices;
    for (const string& card : hand) {
        if (card != "BJ" && card != "RJ") {
            rank_indices.push_back(rank_index(card.substr(1)));
        }
    }
    sort(rank_indices.begin(), rank_indices.end());
    if (is_straight(rank_indices)) {
        return 5;
    }
    if (any_of(rank_counts.begin(), rank_counts.end(), [](const pair<string, int>& p) { return p.second == 3; })) {
        return 4;
    }
    int pair_count = count_if(rank_counts.begin(), rank_counts.end(), [](const pair<string, int>& p) { return p.second == 2; });
    if (pair_count == 2) {
        return 3;
    }
    if (pair_count == 1) {
        return 2;
    }
    return 1;
}

extern "C" int calculate_score(const char* hand[], int hand_size) {
    vector<string> hand_vec(hand, hand + hand_size);
    auto [rank_counts, joker_count] = get_rank_counts(hand_vec);

    vector<int> possible_scores;

    if (joker_count > 0) {
        vector<string> suits_to_check = suits;
        if (is_flush(hand_vec)) {
            suits_to_check = {hand_vec[0].substr(0, 1)};
        }

        for (const string& suit : suits_to_check) {
            vector<string> new_hand = hand_vec;
            for (int i = 0; i < joker_count; ++i) {
                string replacement = suit + ranks[ranks.size() - 1 - i];
                new_hand = replace_jokers(new_hand, replacement);
            }
            unordered_map<string, int> new_rank_counts = get_rank_counts(new_hand).first;
            possible_scores.push_back(calculate_score_without_joker(new_rank_counts, new_hand));
        }
    } else {
        possible_scores.push_back(calculate_score_without_joker(rank_counts, hand_vec));
    }

    return *max_element(possible_scores.begin(), possible_scores.end());
}