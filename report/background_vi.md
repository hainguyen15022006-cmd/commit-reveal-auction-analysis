# Kiến thức nền

Cam kết dựa trên hàm băm cho phép người đấu gửi trước một giá trị để sau đó đối chiếu với giá đấu được công bố. Nhóm sử dụng SHA-256, tạo ra giá trị băm dài 256 bit [1]. Để mở cam kết, người đấu công bố giá đấu và giá trị ngẫu nhiên đã dùng khi tạo cam kết; bên kiểm tra sau đó tính lại giá trị băm. Quá trình này không có bước giải mã. Cam kết cũng không phải chữ ký số và không tự xác định được danh tính người gửi.

Tính chống va chạm có nghĩa là việc tìm hai đầu vào khác nhau cho cùng một giá trị băm là khó về mặt tính toán [2]. Tuy nhiên, riêng tính chất này không giữ được bí mật của giá đấu. Chẳng hạn, miền giá từ 10.000 đến 1.000.000 VND, với bước tăng 10.000 VND, chỉ có 100 khả năng. Nếu cam kết là H(b), người quan sát có thể băm từng giá ứng viên rồi so sánh kết quả. Cách dò này tận dụng miền đầu vào nhỏ mà không cần phá SHA-256.

Vì vậy, mô hình của nhóm bổ sung một giá trị ngẫu nhiên r dài 128 bit, được tạo mới và độc lập cho mỗi cam kết, đồng thời giữ bí mật đến giai đoạn công bố. Khả năng khó đoán của r quan trọng không kém độ dài: một giá trị dài nhưng dễ dự đoán vẫn bảo vệ rất ít. Nhóm cũng dùng cách biểu diễn dữ liệu không nhập nhằng, với thứ tự trường cố định và tiền tố độ dài rõ ràng, để các tổ hợp trường khác nhau không tạo thành cùng một chuỗi byte trước khi băm. Khi dữ liệu được biểu diễn không nhập nhằng và bản ghi cam kết được giữ nguyên, tính chống va chạm hỗ trợ tính ràng buộc. Tính che giấu cần giá trị ngẫu nhiên phù hợp và một giả định bổ sung về hàm băm, chẳng hạn mô hình random oracle [2].

## Tài liệu tham khảo

[1] National Institute of Standards and Technology, Secure Hash Standard (SHS), FIPS PUB 180-4, August 2015, Sec. 1, Fig. 1, p. 3.

[Source](https://doi.org/10.6028/NIST.FIPS.180-4)

[2] MIT 6.5610, Recitation 6: Hash functions, March 17, 2023, Sec. 1, p. 1.

[Source](https://65610.csail.mit.edu/2023/rec/rec6.pdf)
