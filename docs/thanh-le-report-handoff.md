# Bàn giao phần report của Thành Lê

## Nội dung đưa vào bài

Dùng toàn bộ phần viết trong `report/protocol_description_en.md` cho mục 4. Văn bản gồm khoảng 260 từ tiếng Anh, kèm `report/figures/m1_protocol.png`. File `m1_protocol.mmd` là nguồn Mermaid để chỉnh sơ đồ. Khi ghép bài, dùng một bản hình và chỉnh số Figure theo thứ tự trong report.

Phần viết đã có công thức B2, sáu trường Encode với tiền tố độ dài 4 byte big-endian, giá 8 byte, r 16 byte thô, mỗi người một cam kết, biên T1/T2, biên nhận không ký số, loại người không reveal hợp lệ, hòa giá theo mã U và trường hợp không có người thắng. Ví dụ dùng miền giá và thời gian giả định Hải Anh đã xác nhận.

Độ dài mục tiêu là khoảng 0,65 trang gồm hình. Số trang thực tế phụ thuộc cỡ chữ, lề và bố cục tài liệu chung.

## Đối chiếu với code và kết quả

Mô tả được đối chiếu với `docs/model.md`, `src/auction.py` và `src/commitment.py`. Các hàm đã đọc gồm `encode`, `prepare_commitment`, `submit_commit`, `submit_reveal` và `settle`. Quy tắc giao thức là lựa chọn của nhóm. Phần kiến thức nền và nguồn về SHA-256 được trình bày ở Background.

Đã kiểm tra cấu hình và log của Chúc tại nhánh `test/independent-e01-e06`, commit `1ebc862`, file `results/independent_e01_e06_RUN01.json`. Log ghi nhận 37 ca qua, không có lỗi. SHA-256 của `src/auction.py`, `src/commitment.py` và `docs/model.md` khớp với mã nguồn dùng cho lần bàn giao này. Đây là đối chiếu dữ liệu Chúc đã chạy. Bộ 50 bài kiểm thử trên nhánh Thành Lê cũng đã được chạy lại và qua.

## Xuất lại E01

Log E01 cũ lấy hash từ hai file có xuống dòng CRLF trước khi Git lưu LF. Lần bàn giao này đồng nhất xuống dòng LF trước khi chạy và kiểm tra hash khớp cả file thực thi lẫn nội dung Git đã lưu.

Tại thư mục gốc repo, chạy lệnh sau để xuất E01.

```sh
python -m examples.auction_demo --output results/auction_e01.json
```

Log mới ghi thời gian UTC, mã commit mã nguồn, Python và môi trường, cấu hình giá, các biên nhận, trạng thái reveal, kết quả kỳ vọng/thực tế và hash nguồn. Kết quả là U02 thắng với giá 130.000 VND. Mỗi lượt chạy sinh r mới nên commitment thay đổi. Trong report, ghi lần chạy này là kiểm tra tích hợp của Thành Lê.

## Duyệt nhóm

Thành Lê đã chuẩn bị nội dung, hình, code tích hợp và E01 mới. Chúc kiểm tra luật và Dương kiểm tra giả định trước khi nhóm khóa bài. Hải Anh và Hoàng Anh ghép nội dung vào tài liệu chung, kiểm tra dung lượng và số thứ tự hình.
