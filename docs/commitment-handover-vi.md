# Bàn giao mô-đun cam kết cho Thành Lê

Bản này dùng encoding `m1-length-prefixed-be-v1`, theo quy ước nhị phân trong
tin nhắn tích hợp. Python 3.10 trở lên; chỉ dùng thư viện chuẩn.

## File cần dùng

- `commitment.py`: đặt cạnh chương trình gọi, hoặc đưa vào `src/commitment.py`.
- `check_commitment.py`: kiểm tra độc lập mẫu chuẩn trong gói bàn giao.
- `vector.json`: dữ liệu đầu vào, toàn bộ byte đã encode và SHA-256 mong đợi.
- `API.md`: hợp đồng dữ liệu và trách nhiệm của lớp đấu giá.

Giải nén gói và chạy `python check_commitment.py`. Kết quả mong đợi là 8 dòng
`PASS` và mã cam kết bên dưới. Đây là kiểm tra mô-đun, chưa phải E01 của luồng
đấu giá. Sau khi thay mô-đun tạm, Thành Lê chạy lại `python demo_m1.py`.

## Cách gọi

Nếu để file cạnh chương trình gọi:

```python
from commitment import generate_randomness, create_commitment, verify_opening

# Bình thường: tạo r mới, giữ riêng trên phía người đấu đến reveal.
r = generate_randomness()  # str: 32 ký tự hex chữ thường
c = create_commitment("A01", "U01", 100000, r)  # str: 64 ký tự hex

# Khi reveal: đối chiếu với c đã lưu, A hiện tại và người gửi đã xác thực.
ok = verify_opening(c, "A01", "U01", 100000, r)  # True
wrong = verify_opening(c, "A01", "U01", 140000, r)  # False ở mẫu này
```

Nếu giữ cấu trúc repository, đổi dòng import thành `from src.commitment import ...`.
Chữ ký hàm không đổi:

```python
create_commitment(auction_id: str, bidder_id: str, bid: int, randomness: str) -> str
verify_opening(commitment: str, auction_id: str, bidder_id: str,
               bid: int, randomness: str) -> bool
```

**Quan trọng:** r ở giao diện hàm là chuỗi hex; bên trong mới chuyển thành
16 byte thô. Nếu mô-đun tạm của bạn đang lưu `r` dạng `bytes`, truyền `r.hex()`.
Không truyền `r.encode()` và không chuyển giá thành chuỗi. Hàm tạo cam kết báo
`InvalidCommitmentData` (thuộc `ValueError`) khi dữ liệu sai định dạng; hàm kiểm
tra trả `False` nếu đầu vào không hợp lệ hoặc hash không khớp.

## Quy ước byte chốt trong bản bàn giao

Thứ tự sáu trường: `tag, A, U, currency, b, r`.

- `tag = CR-AUCTION-v1`; `currency = VND`; các trường chữ dùng ASCII.
- A và U không rỗng, chỉ gồm chữ/số ASCII, phân biệt hoa thường.
- b là số nguyên dương không dấu, biểu diễn bằng đúng 8 byte big-endian;
  giới hạn biểu diễn là `1 <= b <= 2**64 - 1`.
- r được giải mã từ chuỗi hex thành đúng 16 byte thô.
- **Mỗi trường, kể cả b và r**, được thêm độ dài bằng 4 byte big-endian ở đầu.
  Độ dài tính theo byte. Không có dấu `|` hoặc ký tự xuống dòng.

So với bản cũ, B0 cũng dùng giá 8 byte; B1 dùng hai trường b/r có tiền tố độ dài.
Các hash cũ tạo từ ASCII không dùng lại được với bản này. Cần tạo lại commitment
cho các fixture trước khi chạy. Kết quả chạy cũ vẫn được lưu riêng trong repo.

## Mẫu đầu vào và mã cam kết

Mẫu cố định chỉ để kiểm tra, không dùng r này làm bí mật thật:

```python
r = "00112233445566778899aabbccddeeff"
c = create_commitment("A01", "U01", 100000, r)
expected = "7b4df9d0ff820790c1ef5c2e89ec7b7c7900525b2bdb526abe0b49e187fd2b71"
assert c == expected
assert verify_opening(c, "A01", "U01", 100000, r)
```

Đầu vào băm dài 70 byte. Các đoạn hex dưới đây là sáu trường đã có tiền tố;
ghép liền theo thứ tự để được toàn bộ đầu vào:

```text
0000000d43522d41554354494f4e2d7631
00000003413031
00000003553031
00000003564e44
0000000800000000000186a0
0000001000112233445566778899aabbccddeeff
```

## Phần luồng đấu giá vẫn phải kiểm tra

`verify_opening(...) == True` chỉ xác nhận khớp hash. Lớp điều phối vẫn kiểm tra
phiên, người gửi, miền giá/bước giá, thời hạn, commit trùng, bản ghi đã khóa và
luật chọn người thắng. Không gửi b hoặc r lên bộ điều phối lúc commit.

Sau khi ghép, gửi lại kết quả E01 và bản tích hợp cho Chúc kiểm thử độc lập.
Chưa có mã nguồn `demo_m1.py` ở checkout này nên bản bàn giao không khẳng định
đã chạy hoặc duyệt E01 của Thành Lê.
