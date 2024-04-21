############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/20
# Last modified:   2024/04/21
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################


matrix2d_definition_code = """
template<typename T>
class Matrix2d {

    private:
        std::vector<T> data;
        size_t num_rows;
        size_t num_cols;
        size_t row_start;
        size_t col_start;

    public:

        void init(size_t first_row_idx, size_t last_row_idx,
                  size_t first_col_idx, size_t last_col_idx) {
            this->num_rows = last_row_idx - first_row_idx + 1;
            this->num_cols = last_col_idx - first_col_idx + 1;
            this->row_start = first_row_idx;
            this->col_start = first_col_idx;
            this->data.resize(this->num_rows * this->num_cols);
        }

        T& operator()(size_t i, size_t j) {
            return data.at((i-row_start)*num_rows + (j-col_start));
        }

        int get_row_start_index() {
            return row_start;
        }

        int get_row_last_index() {
            return row_start + num_rows - 1;
        }

        int get_col_start_index() {
            return col_start;
        }

        int get_col_last_index() {
            return col_start + num_cols - 1;
        }
};
"""


trimatrix2d_definition_code = """
template<typename T>
class TriMatrix2d {

    private:
        std::vector<T> data;
        size_t size;
        size_t row_ofs;
        size_t col_ofs;
        bool lower;

    public:

        void init(size_t first_row_idx, size_t last_row_idx,
                  size_t first_col_idx, size_t last_col_idx, bool lower) {
            int num_rows = last_row_idx - first_row_idx + 1;
            int num_cols = last_col_idx - first_col_idx + 1;
            if (num_rows != num_cols) {
                throw std::runtime_error("number of rows and cols does not match");
            }
            size = num_rows;
            size_t numel = size*(size+1) / 2;
            this->data.resize(numel);
            this->row_ofs = first_row_idx;
            this->col_ofs = first_col_idx;
            this->lower = lower;
        }

        T& operator()(size_t i, size_t j) {
            size_t shift_row_idx = i - row_ofs;
            size_t shift_col_idx = j - col_ofs;
            if (! lower) {
                shift_col_idx = size - 1 - shift_col_idx;
            }
            if (shift_row_idx < shift_col_idx) {
                throw std::runtime_error("elements only available on other side of diagonal");
            }
            size_t ofs = shift_row_idx * (shift_row_idx+1) / 2 + shift_col_idx;
            return data.at(ofs);
        }

        int get_row_start_index() {
            return row_ofs;
        }

        int get_row_last_index() {
            return row_ofs + size - 1;
        }

        int get_col_start_index() {
            return col_ofs;
        }

        int get_col_last_index() {
            return col_ofs + size - 1;
        }
};
"""
