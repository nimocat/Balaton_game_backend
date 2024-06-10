#include <stdio.h>
#include <stdlib.h>
#include <string.h>

const char *suits[] = {"H", "S", "D", "C"};
const char *ranks[] = {"2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"};
const char *jokers[] = {"BJ", "RJ"};

int rank_index(char rank) {
    for (int i = 0; i < 13; i++) {
        if (ranks[i][0] == rank) {
            return i;
        }
    }
    return -1;
}

int is_flush(const char *hand[], int hand_size) {
    char suit = hand[0][0];
    for (int i = 0; i < hand_size; i++) {
        if (hand[i][0] != suit && strcmp(hand[i], "BJ") != 0 && strcmp(hand[i], "RJ") != 0) {
            return 0;
        }
    }
    return 1;
}

int is_straight(int rank_indices[], int size, int joker_count) {
    for (int i = 0; i < size - 1; i++) {
        if (rank_indices[i + 1] - rank_indices[i] != 1) {
            if (joker_count > 0) {
                joker_count--;
                continue;
            }
            return 0;
        }
    }
    return 1;
}

int calculate_hand_score(int rank_counts[], int joker_count, int hand_size, int *is_flush_hand) {
    int pair_count = 0;
    int three_count = 0;
    int four_count = 0;
    
    for (int i = 0; i < 13; i++) {
        if (rank_counts[i] == 2) pair_count++;
        else if (rank_counts[i] == 3) three_count++;
        else if (rank_counts[i] == 4) four_count++;
    }

    if (joker_count > 0) {
        if (is_flush_hand && is_straight(rank_counts, hand_size, joker_count)) return 15;
        if (is_flush_hand) return 7;
        if (is_straight(rank_counts, hand_size, joker_count)) return 5;
        if (four_count > 0 || (three_count > 0 && joker_count >= 1)) return 12;
        if (three_count > 0 && pair_count > 0) return 9;
        if (three_count > 0) return 4;
        if (pair_count >= 2 || (pair_count == 1 && joker_count >= 1)) return 3;
        if (pair_count == 1) return 2;
    } else {
        if (is_flush_hand && is_straight(rank_counts, hand_size, joker_count)) return 15;
        if (is_flush_hand) return 7;
        if (is_straight(rank_counts, hand_size, joker_count)) return 5;
        if (four_count > 0) return 12;
        if (three_count > 0 && pair_count > 0) return 9;
        if (three_count > 0) return 4;
        if (pair_count >= 2) return 3;
        if (pair_count == 1) return 2;
    }
    
    return 1;
}

int calculate_score_without_joker(const char *hand[], int hand_size) {
    int rank_counts[13] = {0};
    int joker_count = 0;
    int rank_indices[hand_size];
    int rank_count = 0;
    int is_flush_hand = is_flush(hand, hand_size);
    
    for (int i = 0; i < hand_size; i++) {
        if (strcmp(hand[i], "BJ") == 0 || strcmp(hand[i], "RJ") == 0) {
            joker_count++;
        } else {
            int rank_idx = rank_index(hand[i][1]);
            rank_counts[rank_idx]++;
            rank_indices[rank_count++] = rank_idx;
        }
    }

    qsort(rank_indices, rank_count, sizeof(int), (int (*)(const void *, const void *))strcmp);

    return calculate_hand_score(rank_counts, joker_count, hand_size, is_flush_hand);
}

int calculate_score(const char *hand[], int hand_size) {
    return calculate_score_without_joker(hand, hand_size);
}
