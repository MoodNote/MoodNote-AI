# MoodNote - Đặc tả Yêu cầu Phần mềm (Software Requirements Specification - SRS)

_Tài liệu này được xây dựng theo chuẩn IEEE 830, mô tả chi tiết các yêu cầu chức năng và phi chức năng của hệ thống MoodNote._

**Version:** 2.0
**Status:** Ready for Review
**Last Updated:** 2026-01-29

---

## Table of Contents

1. [Giới thiệu](#1-giới-thiệu)
    - 1.1 Mục đích
    - 1.2 Phạm vi hệ thống
    - 1.3 Định nghĩa, từ viết tắt
2. [Mô tả tổng quan](#2-mô-tả-tổng-quan)
    - 2.1 Đặc điểm người dùng
    - 2.2 Môi trường hoạt động
    - 2.3 Ràng buộc hệ thống
3. [Yêu cầu chức năng](#3-yêu-cầu-chức-năng)
    - 3.1 Người dùng và xác thực (FR-01 đến FR-04)
    - 3.2 Nhật ký (FR-06 đến FR-09)
    - 3.3 Phân tích cảm xúc (FR-10 đến FR-13)
    - 3.4 Gợi ý âm nhạc (FR-14 đến FR-17)
    - 3.5 Thống kê (FR-18 đến FR-20)
    - 3.6 Thông báo (FR-21)
    - 3.7 Admin Dashboard (FR-22 đến FR-26)
4. [Yêu cầu phi chức năng](#4-yêu-cầu-phi-chức-năng-non-functional-requirements)
    - 4.1 Performance (NFR-01 đến NFR-05)
    - 4.2 Security (NFR-06 đến NFR-11)
    - 4.3 Usability (NFR-12 đến NFR-16)
    - 4.4 Reliability (NFR-17 đến NFR-19)
    - 4.5 Maintainability (NFR-20 đến NFR-21)
    - 4.6 Compatibility (NFR-22 đến NFR-24)
5. [Use Cases và User Stories](#5-use-cases-và-user-stories)
    - 5.1 Use Case Diagram Overview
    - 5.2 Use Cases chi tiết (UC-01 đến UC-04)
    - 5.3 User Stories (US-01 đến US-20, 20 stories total)
6. [Phạm vi Dự án](#6-phạm-vi-dự-án-project-scope)
    - 6.1 MVP (Minimum Viable Product)
    - 6.2 Advanced Features
7. [Data Requirements](#7-data-requirements-yêu-cầu-về-dữ-liệu)
    - 7.1-7.6 Các loại dữ liệu
    - 7.7 Data Privacy và Security
8. [External Interface Requirements](#8-external-interface-requirements-yêu-cầu-giao-diện-bên-ngoài)
    - 8.1 User Interface Requirements
    - 8.2 Third-Party API Requirements
    - 8.3 Hardware Interface Requirements
    - 8.4 Communication Interfaces
9. [Giả định và Phụ thuộc](#9-giả-định-và-phụ-thuộc-assumptions-and-dependencies)
    - 9.1 Assumptions
    - 9.2 Dependencies
10. [Risk Analysis](#10-risk-analysis-phân-tích-rủi-ro)
    - 10.1 Technical Risks
    - 10.2 Business/User Risks
    - 10.3 Legal/Compliance Risks
    - 10.4 Project Risks
11. [Success Criteria](#11-success-criteria-tiêu-chí-thành-công)
    - 11.1 MVP Success Criteria
    - 11.2 Advanced Features Success Criteria
    - 11.3 Project Deliverables
12. [Kết luận](#12-kết-luận-conclusion)
    - 12.1 Tóm tắt tài liệu
    - 12.2 Tính khả thi
    - 12.3 Next Steps
    - 12.4 Document Maintenance

---

## 1. Giới thiệu

### 1.1 Mục đích

Tài liệu này nhằm mục đích mô tả một cách đầy đủ và chi tiết các yêu cầu của hệ thống MoodNote – một ứng dụng hỗ trợ ghi chép nhật ký cảm xúc và gợi ý âm nhạc thông minh. Tài liệu được sử dụng làm cơ sở cho quá trình:

- Phân tích và thiết kế hệ thống
- Lập trình và triển khai
- Kiểm thử và đánh giá chất lượng

Đối tượng đọc tài liệu bao gồm: giảng viên hướng dẫn, nhóm phát triển phần mềm, và các bên liên quan khác.

### 1.2 Phạm vi hệ thống

MoodNote là một hệ thống cho phép người dùng:

- Ghi lại nhật ký cảm xúc hằng ngày dưới dạng văn bản hoặc giọng nói
- Phân tích cảm xúc thông qua AI
- Nhận gợi ý âm nhạc phù hợp với tâm trạng
- Theo dõi sự thay đổi cảm xúc theo thời gian

Hệ thống bao gồm các thành phần chính:

- **Mobile Application (Ứng dụng di động):** Android (ưu tiên cho phạm vi đồ án cá nhân)
- **Admin Dashboard (Web):** Quản lý user, quản lý database nhạc, và analytics
- **Backend API:** Xử lý logic nghiệp vụ và lưu trữ dữ liệu
- **AI Emotion Service (Dịch vụ phân tích cảm xúc AI):** Phân tích ngôn ngữ tự nhiên tiếng Việt
- **Music Service (Dịch vụ âm nhạc):** Database âm nhạc nội bộ với metadata bài hát

**Hệ thống bao gồm:**

- Quản lý người dùng và xác thực
- Ghi chép và quản lý nhật ký cảm xúc
- Phân tích cảm xúc tự động bằng AI
- Gợi ý âm nhạc dựa trên cảm xúc
- Thống kê và visualize dữ liệu cảm xúc
- Thông báo và nhắc nhở thông minh

**Lưu ý quan trọng - Hệ thống KHÔNG bao gồm:**

- Chức năng thanh toán/subscription
- Tư vấn tâm lý chuyên nghiệp/telemedicine
- Chẩn đoán bệnh lý tâm thần
- Kết nối với bác sĩ/chuyên gia tâm lý
- Chia sẻ nhật ký công khai/mạng xã hội

### 1.3 Định nghĩa, từ viết tắt

| Thuật ngữ    | Mô tả                                                            |
| ------------ | ---------------------------------------------------------------- |
| SRS          | Software Requirements Specification – Đặc tả yêu cầu phần mềm    |
| NLP          | Natural Language Processing – Xử lý ngôn ngữ tự nhiên            |
| AI           | Artificial Intelligence – Trí tuệ nhân tạo                       |
| JWT          | JSON Web Token – Token xác thực người dùng                       |
| API          | Application Programming Interface – Giao diện lập trình ứng dụng |
| Sentiment    | Độ tích cực/tiêu cực của cảm xúc (thang đo -1 đến +1)            |
| Emotion      | Loại cảm xúc cụ thể (vui, buồn, tức giận, lo lắng, v.v.)         |
| Mirror Mode  | Gợi ý nhạc cùng tâm trạng hiện tại của người dùng                |
| Shift Mode   | Gợi ý nhạc giúp cải thiện/chuyển đổi tâm trạng                   |
| Tag          | Nhãn phân loại do người dùng gắn vào nhật ký                     |
| Mood Entry   | Một bản ghi nhật ký cảm xúc                                      |
| Offline Mode | Chế độ sử dụng ứng dụng không cần kết nối Internet               |

---

## 2. Mô tả tổng quan

### 2.1 Đặc điểm người dùng

Người dùng chính của hệ thống bao gồm:

1. **Sinh viên:** Thường xuyên chịu áp lực học tập, cần công cụ ghi chép cảm xúc.
2. **Người đi làm:** Cần theo dõi stress và tâm trạng.
3. **Người quan tâm sức khỏe tinh thần:** Mong muốn cải thiện cảm xúc mỗi ngày.

Các nhóm người dùng này có trình độ sử dụng smartphone cơ bản, không yêu cầu kiến thức kỹ thuật chuyên sâu.

### 2.2 Môi trường hoạt động

- **Platform (Nền tảng):** Mobile (Android/Cross Platform), Admin Dashboard (Web)
- **Backend (Máy chủ):** Node.js Server
- **Database (Cơ sở dữ liệu):** PostgreSQL/MongoDB
- **Internet:** Kết nối Internet không bắt buộc cho các chức năng cơ bản.
  Người dùng có thể sử dụng hệ thống ở chế độ offline để ghi nhật ký.
  Tuy nhiên, các chức năng nâng cao như phân tích cảm xúc, đồng bộ dữ liệu và gợi ý âm nhạc yêu cầu kết nối Internet.

### 2.3 Ràng buộc hệ thống (Mọi ràng buộc diều mang tính tương đối)

#### 2.3.1 Ràng buộc về công nghệ

- Hệ thống phải hỗ trợ tiếng Việt cho chức năng phân tích cảm xúc
- Ứng dụng mobile phải tương thích với Android 8.0+
- Admin Dashboard (Web) phải hỗ trợ các trình duyệt: Chrome, Firefox (2 phiên bản gần nhất)
- Hệ thống phải hoạt động được trên thiết bị có RAM tối thiểu 2GB

#### 2.3.2 Ràng buộc về dữ liệu

- Dữ liệu người dùng phải được mã hóa khi lưu trữ
- Mỗi bản ghi nhật ký không được vượt quá 5000 ký tự
- Voice input xử lý real-time
- Hệ thống phải lưu trữ lịch sử nhật ký tối thiểu 2 năm

#### 2.3.3 Ràng buộc về AI/NLP

- Mô hình AI phải được train trên dữ liệu tiếng Việt
- Độ chính xác phân tích cảm xúc tối thiểu 75% (so với đánh giá của con người)
- Thời gian phản hồi phân tích cảm xúc không quá 3 giây cho văn bản dưới 1000 ký tự
- Hệ thống phải xử lý được tiếng Việt có dấu và không dấu

#### 2.3.4 Ràng buộc về database âm nhạc

- Database âm nhạc phải chứa metadata đầy đủ: tên bài, nghệ sĩ, album, thể loại, mood tags
- Mỗi bài hát phải được gắn mood tags phù hợp với 6 loại cảm xúc chính
- Database cần có ít nhất 500-1000 bài hát để đảm bảo đa dạng
- Hỗ trợ tìm kiếm và filter theo mood, genre, nghệ sĩ

#### 2.3.6 Ràng buộc về pháp lý và quyền riêng tư

- Tuân thủ quy định bảo vệ dữ liệu cá nhân của Việt Nam (Nghị định 13/2023/NĐ-CP)
- Người dùng phải được thông báo rõ ràng về việc thu thập và sử dụng dữ liệu
- Hệ thống không được chia sẻ dữ liệu cá nhân cho bên thứ ba mà không có sự đồng ý

#### 2.3.7 Ràng buộc về tài nguyên (Dự án đồ án)

- Dự án triển khai trong môi trường học tập, không yêu cầu infrastructure quy mô lớn
- Hệ thống thiết kế để demo và testing, chưa tối ưu cho production scale

---

## 3. Yêu cầu chức năng (Mọi yêu cầu chức năng đều là giả định do người lập trình tạo ra)

### 3.1 Người dùng và xác thực

- **FR-01: Đăng ký tài khoản**
  Hệ thống cho phép người dùng tạo tài khoản mới bằng email và mật khẩu. Sau khi đăng ký thành công, hệ thống lưu thông tin người dùng vào cơ sở dữ liệu.

    **Acceptance Criteria:**
    - Email phải đúng định dạng (có @ và domain)
    - Email chưa được đăng ký trong hệ thống
    - Mật khẩu đáp ứng NFR-10 (8+ ký tự, chữ hoa, chữ thường, số, ký tự đặc biệt)
    - Mật khẩu và xác nhận mật khẩu phải trùng khớp
    - Email xác thực được gửi trong vòng 1 phút
    - Link xác thực có hiệu lực 24 giờ
    - Sau khi xác thực email, tài khoản được kích hoạt

- **FR-02: Đăng nhập**
  Người dùng có thể đăng nhập bằng email và mật khẩu để truy cập hệ thống.

    **Acceptance Criteria:**
    - Chấp nhận email (không phân biệt hoa thường)
    - Xác thực mật khẩu chính xác
    - Tài khoản đã được kích hoạt (email verified)
    - Tạo JWT token với expiration 24 giờ
    - Lưu refresh token với expiration 7 ngày
    - Thời gian đăng nhập < 2 giây (NFR-01)

- **FR-03: Quên mật khẩu**
  Hệ thống hỗ trợ gửi email reset mật khẩu khi người dùng quên mật khẩu.

    **Acceptance Criteria:**
    - Nhập email đã đăng ký
    - Gửi email chứa OTP reset trong vòng 1 phút
    - Reset OTP có hiệu lực 1 giờ
    - OTP reset chỉ sử dụng được 1 lần
    - Sau khi reset thành công, invalidate tất cả sessions cũ
    - Nếu email không tồn tại, không tiết lộ thông tin (security best practice)

- **FR-04: Đổi mật khẩu**
  Người dùng có thể thay đổi mật khẩu sau khi đã đăng nhập. Hệ thống yêu cầu xác thực mật khẩu cũ trước khi cho phép cập nhật mật khẩu mới. Mật khẩu mới phải đáp ứng các tiêu chí bảo mật (độ dài tối thiểu, chứa ký tự đặc biệt, số, chữ hoa).

    **Acceptance Criteria:**
    - Phải đăng nhập để thực hiện
    - Nhập đúng mật khẩu hiện tại
    - Mật khẩu mới khác mật khẩu cũ
    - Mật khẩu mới đáp ứng NFR-10
    - Xác nhận mật khẩu mới phải khớp
    - Sau khi đổi thành công, gửi email thông báo
    - Invalidate các sessions khác (trừ session hiện tại)

### 3.2 Nhật ký

- **FR-06: Tạo nhật ký**
  Người dùng có thể tạo một bản ghi nhật ký mới, nhập nội dung cảm xúc dưới dạng văn bản.

    **Acceptance Criteria:**
    - Nội dung từ 10 đến 5000 ký tự
    - Hỗ trợ tiếng Việt có dấu và không dấu
    - Hỗ trợ emoji và ký tự đặc biệt
    - **Tự động lưu:**
        - Auto-save mỗi 5-10 giây khi người dùng đang nhập
        - Auto-save khi người dùng rời khỏi text editor (onBlur/unfocus)
        - Hiển thị trạng thái "Đang lưu..." và "Đã lưu" (subtle indicator)
    - Hoạt động offline, đồng bộ khi có mạng
    - Timestamp tự động (ngày giờ tạo)
    - Lưu thành công trong < 1 giây (NFR-01)
    - Không có button "Lưu" hoặc "Confirm", mọi thay đổi được lưu tự động

- **FR-07: Voice Input (Nhập liệu bằng giọng nói)**
  Người dùng có thể ghi âm giọng nói real-time, hệ thống sẽ chuyển đổi thành văn bản trực tiếp.

    **Acceptance Criteria:**
    - **Xử lý real-time** sử dụng thư viện React Native (ví dụ: react-native-voice, @react-native-voice/voice)
    - Chuyển đổi giọng nói thành văn bản real-time (hiển thị từng câu khi nói)
    - Hỗ trợ tiếng Việt (vi-VN)
    - Hiển thị visual indicator khi đang ghi âm (microphone animation)
    - Cho phép tạm dừng/tiếp tục ghi âm
    - Cho phép chỉnh sửa văn bản sau khi hoàn thành
    - Không lưu file âm thanh gốc (chỉ lưu văn bản đã convert)
    - Yêu cầu microphone permission
    - Xử lý error khi không có quyền truy cập microphone
    - Thông báo khi Speech-to-Text service không khả dụng

- **FR-08: Gắn Tag (Thẻ)**
  Người dùng có thể gắn các nhãn như "stress", "happy", "work" để phân loại nhật ký.

    **Acceptance Criteria:**
    - Gắn được 0-5 tags mỗi nhật ký
    - Gợi ý tags đã sử dụng trước đó (autocomplete)
    - Có thể tạo tag mới
    - Tag không phân biệt hoa thường
    - Tag không chứa ký tự đặc biệt (chỉ chữ cái, số, gạch ngang)
    - Độ dài tag: 2-20 ký tự
    - Hiển thị tag dưới dạng chips/badges
    - Có thể xóa tag khỏi nhật ký
    - Hỗ trợ search/filter theo tags

- **FR-09: Sửa/Xóa nhật ký**
  Người dùng có thể chỉnh sửa hoặc xóa các nhật ký đã tạo trước đó.

    **Acceptance Criteria:**
    - **Sửa:**
        - Có thể sửa nội dung, tags
        - Không thể sửa timestamp (giữ nguyên thời điểm tạo)
        - Lưu "last modified" timestamp
        - **Tự động lưu:**
            - Auto-save mỗi 5-10 giây khi đang chỉnh sửa
            - Auto-save khi người dùng rời khỏi text editor
            - Hiển thị trạng thái "Đang lưu..." và "Đã lưu"
        - Nếu sửa nội dung → chạy lại emotion analysis tự động
        - Không có button "Lưu" hoặc "Confirm", mọi thay đổi được lưu tự động
    - **Xóa:**
        - Hiển thị confirmation dialog "Bạn có chắc chắn?"
        - Xóa vĩnh viễn, không thể khôi phục
        - Xóa cả emotion analysis và recommendations liên quan
        - Swipe-to-delete trên mobile (UX convenience)
        - Cập nhật statistics sau khi xóa

### 3.3 Phân tích cảm xúc

- **FR-10: Phân tích cảm xúc**
  Hệ thống sử dụng AI để phân tích nội dung nhật ký và xác định cảm xúc chính.

    **Yêu cầu chi tiết:**
    - Hỗ trợ phân tích văn bản tiếng Việt có dấu và không dấu
    - Nhận diện ít nhất 6 loại cảm xúc cơ bản: Vui vẻ, Buồn, Tức giận, Lo lắng, Sợ hãi, Bình thường
    - Xử lý được văn bản từ 10 đến 5000 ký tự
    - Có khả năng xử lý ngôn ngữ đời thường, teencode, và emoji
    - Kết quả phân tích phải bao gồm: loại cảm xúc chính, sentiment score, intensity, và keywords

- **FR-11: Sentiment Score (Điểm cảm xúc)**
  Hệ thống trả về giá trị từ -1 (rất tiêu cực) đến +1 (rất tích cực).

    **Yêu cầu chi tiết:**
    - Thang đo: -1.0 đến +1.0 (số thực, làm tròn 2 chữ số thập phân)
    - Phân loại:
        - Rất tiêu cực: -1.0 đến -0.6
        - Tiêu cực: -0.6 đến -0.2
        - Trung tính: -0.2 đến +0.2
        - Tích cực: +0.2 đến +0.6
        - Rất tích cực: +0.6 đến +1.0
    - Score phải được tính toán dựa trên toàn bộ ngữ cảnh của văn bản

- **FR-12: Intensity (Cường độ cảm xúc)**
  Xác định mức độ mạnh/yếu của cảm xúc.

    **Yêu cầu chi tiết:**
    - Thang đo: 0 đến 100 (số nguyên)
    - Phân loại:
        - Rất yếu: 0-20
        - Yếu: 21-40
        - Trung bình: 41-60
        - Mạnh: 61-80
        - Rất mạnh: 81-100
    - Intensity được tính độc lập với sentiment (cảm xúc tiêu cực cũng có thể có intensity cao)

- **FR-13: Keywords (Từ khóa)**
  Trích xuất các từ khóa quan trọng trong nội dung nhật ký.

    **Yêu cầu chi tiết:**
    - Trích xuất 3-10 từ khóa quan trọng nhất
    - Ưu tiên từ khóa liên quan đến cảm xúc và sự kiện
    - Loại bỏ stopwords tiếng Việt
    - Hỗ trợ cả từ đơn và cụm từ (1-3 từ)
    - Keywords được sắp xếp theo mức độ quan trọng (relevance score)

### 3.4 Gợi ý âm nhạc

- **FR-14: Mirror Mode (Chế độ phản chiếu cảm xúc)**
  Gợi ý danh sách nhạc có cùng cảm xúc với người dùng.

    **Yêu cầu chi tiết:**
    - Dựa trên sentiment score và loại cảm xúc để tìm nhạc phù hợp từ database nội bộ
    - Gợi ý 10-20 bài hát mỗi lần
    - Ánh xạ cảm xúc sang mood tags và thể loại nhạc:
        - Vui vẻ → Tags: happy, upbeat, energetic | Genres: Pop, Dance
        - Buồn → Tags: sad, melancholic, emotional | Genres: Ballad, Acoustic
        - Tức giận → Tags: angry, intense, powerful | Genres: Rock, Metal
        - Lo lắng → Tags: calm, relaxing, peaceful | Genres: Chill, Ambient
        - Sợ hãi → Tags: comforting, gentle, soothing | Genres: Soft, Instrumental
        - Bình thường → Tags: neutral, balanced | Genres: Mix of genres
    - Query database với mood tags phù hợp
    - Thuật toán gợi ý: kết hợp mood tags + sentiment score range + randomization
    - Hiển thị thông tin: tên bài, nghệ sĩ, album, thể loại, năm phát hành
    - Cho phép người dùng bỏ qua bài hát không thích và refresh để lấy gợi ý mới

- **FR-15: Shift Mode (Chế độ chuyển đổi cảm xúc)**
  Gợi ý nhạc giúp cải thiện tâm trạng.

    **Yêu cầu chi tiết:**
    - Áp dụng cho cảm xúc tiêu cực (sentiment < -0.2)
    - Gợi ý nhạc có mood tích cực hơn để cải thiện tâm trạng
    - Chuyển đổi dần: nếu sentiment hiện tại là -0.8, gợi ý nhạc có mood -0.3 → 0 → +0.5
    - Gợi ý 15-25 bài hát được sắp xếp theo thứ tự tăng dần độ tích cực
    - Ưu tiên thể loại: Motivational, Happy, Energetic, Hopeful
    - Tránh gợi ý nhạc quá vui nếu người dùng đang rất buồn (để tránh tâm lý phản cảm)

- **FR-16: Playlist tự động**
  Tạo playlist dựa trên lịch sử cảm xúc.

    **Yêu cầu chi tiết:**
    - Phân tích lịch sử 7-30 ngày gần nhất
    - Tạo playlist dựa trên:
        - Cảm xúc xuất hiện nhiều nhất
        - Thời điểm trong ngày (sáng/chiều/tối)
        - Tag người dùng thường dùng
    - Tự động cập nhật playlist hàng tuần
    - Mỗi playlist chứa 20-50 bài hát
    - Cho phép người dùng tùy chỉnh tiêu chí tạo playlist

- **FR-17: Lưu playlist cá nhân**
  Hệ thống cho phép lưu và quản lý các playlist đã được gợi ý để người dùng có thể xem lại sau.

    **Yêu cầu chi tiết:**
    - Cho phép lưu playlist với tên tùy chỉnh
    - Hiển thị danh sách các playlist đã lưu
    - Mỗi playlist hiển thị: tên, số bài hát, ngày tạo, mood liên quan
    - Cho phép chỉnh sửa (thêm/xóa bài hát từ database) và xóa playlist
    - Giới hạn tối đa 50 playlist được lưu
    - Mỗi playlist có thể chứa tối đa 100 bài hát

### 3.5 Thống kê

- **FR-18: Biểu đồ cảm xúc**
  Hiển thị biểu đồ thể hiện sự thay đổi cảm xúc theo thời gian.

    **Acceptance Criteria:**
    - Hiển thị line chart với sentiment score theo ngày
    - Trục X: Thời gian (ngày)
    - Trục Y: Sentiment score (-1 đến +1)
    - Màu sắc: gradient từ đỏ (tiêu cực) → xanh (tích cực)
    - Có thể zoom vào khoảng thời gian cụ thể
    - Cho phép chọn time range: 7/14/30/90 ngày hoặc custom
    - Hiển thị average sentiment score cho period
    - Hiển thị trend line (xu hướng tăng/giảm/ổn định)
    - Click vào data point → xem nhật ký của ngày đó
    - Export biểu đồ dưới dạng image (PNG)
    - Load time < 3 giây (NFR-01)

- **FR-19: Thống kê từ khóa**
  Thống kê các từ khóa xuất hiện nhiều nhất.

    **Acceptance Criteria:**
    - Hiển thị top 10-20 keywords
    - Sắp xếp theo frequency (cao → thấp)
    - Hiển thị số lần xuất hiện của mỗi keyword
    - Word cloud visualization (tùy chọn)
    - Kích thước từ tỉ lệ với frequency
    - Click vào keyword → xem các nhật ký chứa keyword đó
    - Lọc theo time range
    - Loại bỏ stopwords tiếng Việt
    - Có thể lọc theo tags
    - Group các từ tương tự (lemmatization nếu có)

- **FR-20: Patterns (Xu hướng cảm xúc)**
  Hệ thống nhận diện các xu hướng cảm xúc lặp lại.

    **Acceptance Criteria:**
    - Phân tích ít nhất 30 ngày dữ liệu
    - Nhận diện patterns theo:
        - Thời gian trong ngày (sáng/chiều/tối)
        - Ngày trong tuần (thứ 2-CN)
        - Tags thường đi kèm với emotion nào
    - Hiển thị insights dễ hiểu:
        - "Bạn thường buồn vào tối Chủ Nhật"
        - "Bạn vui nhất vào sáng thứ 6"
        - "Tag 'work' thường đi kèm với cảm xúc stress"
    - Confidence level cho mỗi pattern (%)
    - Gợi ý hành động dựa trên patterns
    - Cập nhật patterns mỗi tuần
    - Chỉ hiển thị patterns có statistical significance

### 3.6 Thông báo

- **FR-21: Reminder (Nhắc nhở)**
  Gửi thông báo nhắc người dùng viết nhật ký mỗi ngày.

    **Acceptance Criteria:**
    - Có thể bật/tắt trong Settings
    - Tùy chỉnh thời gian nhận thông báo (mặc định: 21:00)
    - Tùy chỉnh tần suất: Hàng ngày, Một số ngày trong tuần
    - Nội dung thông báo thân thiện, động viên:
        - "Hôm nay bạn thế nào? Hãy chia sẻ với MoodNote nhé 💙"
        - "Đã 2 ngày bạn chưa viết nhật ký. Hãy dành 5 phút cho bản thân!"
    - Smart reminder: không gửi nếu đã viết trong ngày
    - Streak tracking: "Bạn đã viết liên tục 7 ngày! 🔥"
    - Không spam: tối đa 1 notification/ngày

### 3.7 Admin Dashboard (Web)

- **FR-22: Admin Authentication**
  Admin có thể đăng nhập vào dashboard để quản lý hệ thống.

    **Acceptance Criteria:**
    - Admin login riêng biệt với user login
    - Session timeout sau 1 giờ không hoạt động

- **FR-23: User Management**
  Admin có thể xem và quản lý danh sách người dùng.

    **Acceptance Criteria:**
    - Hiển thị danh sách users với pagination (50 users/page)
    - Filter theo: ngày đăng ký, trạng thái (active/inactive), số lượng entries
    - Search user theo email hoặc username
    - Xem chi tiết thông tin user:
        - Thông tin cơ bản (email, ngày tạo, last login)
        - Tổng số entries, số ngày viết nhật ký
        - Statistics tổng quan (emotion distribution)
    - Khóa/mở khóa tài khoản user (soft delete)
    - Không xem được nội dung nhật ký của user (privacy)

- **FR-24: Music Database Management**
  Admin có thể quản lý database âm nhạc nội bộ.

    **Acceptance Criteria:**
    - CRUD operations cho bài hát:
        - Thêm bài hát mới (form với các trường: title, artist, album, genre, mood tags, sentiment range)
        - Chỉnh sửa metadata
        - Xóa bài hát
    - Bulk import songs từ CSV file
    - Filter và search:
        - Filter theo genre, mood tags
        - Search theo title, artist
    - Hiển thị:
        - Danh sách bài hát với pagination (100 songs/page)
        - Số lượng bài hát theo từng mood tag
        - Số lượng bài hát theo genre
    - Validate:
        - Mỗi bài hát phải có ít nhất 1 mood tag
        - Sentiment range hợp lệ (-1.0 đến 1.0)

- **FR-25: Analytics Dashboard**
  Admin có thể xem các thống kê tổng quan về hệ thống.

    **Acceptance Criteria:**
    - User Analytics:
        - Tổng số users (active/inactive)
        - New users theo ngày/tuần/tháng (chart)
        - Daily Active Users (DAU), Monthly Active Users (MAU)
        - Retention rate
    - Content Analytics:
        - Tổng số entries được tạo
        - Entries per day (chart)
        - Emotion distribution across all users (pie chart)
        - Top keywords trending
    - Music Analytics:
        - Top 20 bài hát được recommend nhiều nhất
        - Top 20 bài hát được play nhiều nhất
        - Genre distribution
        - Mood tag usage statistics
    - System Health:
        - API response time trung bình
        - Error rate
        - Database size

<!-- - **FR-26: System Configuration**
  Admin có thể cấu hình các settings của hệ thống.

    **Acceptance Criteria:**
    - Cấu hình AI/ML thresholds:
        - Minimum confidence score để hiển thị emotion
        - Sentiment range boundaries
    - Cấu hình recommendation algorithm:
        - Number of songs to recommend
        - Randomization factor
    - Maintenance mode:
        - Bật/tắt maintenance mode
        - Custom maintenance message
    - Export data:
        - Export user statistics (anonymized)
        - Export music database
        - Export system logs -->

---

## 4. Yêu cầu phi chức năng (Non-Functional Requirements)

### 4.1 Performance (Hiệu năng)

- **NFR-01: Thời gian phản hồi API**
    - API đăng nhập/đăng ký: ≤ 2 giây
    - API tạo/sửa/xóa nhật ký: ≤ 1 giây
    - API phân tích cảm xúc: ≤ 3 giây (cho văn bản < 1000 ký tự)
    - API gợi ý nhạc: ≤ 5 giây
    - API lấy thống kê: ≤ 2 giây

- **NFR-02: Thời gian tải giao diện**
    - Màn hình đăng nhập: ≤ 1 giây
    - Màn hình chính (dashboard): ≤ 2 giây
    - Màn hình thống kê: ≤ 3 giây (có biểu đồ)
    - Chuyển đổi giữa các màn hình: ≤ 0.5 giây

- **NFR-03: Voice-to-Text Processing**
    - Xử lý real-time sử dụng thư viện React Native
    - Chuyển đổi giọng nói thành văn bản trong thời gian thực
    - Latency tối đa: 2 giây cho mỗi câu nói
    - Hỗ trợ tiếng Việt (vi-VN)

- **NFR-04: Offline Performance**
    - Tất cả chức năng ghi nhật ký phải hoạt động offline
    - Dữ liệu offline được đồng bộ tự động khi có kết nối
    - Thời gian đồng bộ: ≤ 10 giây cho 100 bản ghi

- **NFR-05: Scalability (Khả năng mở rộng)**
    - Hỗ trợ ít nhất 100 người dùng đồng thời (cho phạm vi đồ án)
    - Mỗi người dùng có thể lưu tối đa 1000 bản ghi nhật ký
    - Database có thể lưu trữ dữ liệu của 1000+ người dùng

### 4.2 Security (Bảo mật)

- **NFR-06: Mã hóa mật khẩu**
    - Sử dụng thuật toán bcrypt hoặc Argon2
    - Salt rounds tối thiểu: 10
    - Không lưu mật khẩu dạng plain text

- **NFR-07: Xác thực và phân quyền**
    - Sử dụng JWT với expiration time 24 giờ
    - Refresh token có thời hạn 7 ngày
    - Session timeout sau 30 phút không hoạt động

- **NFR-08: Quyền riêng tư dữ liệu**
    - Mỗi người dùng chỉ truy cập được dữ liệu của chính mình
    - Không có chức năng admin đọc nhật ký của người dùng
    - Dữ liệu nhật ký được mã hóa trong database

- **NFR-09: Chính sách mật khẩu**
    - Độ dài tối thiểu: 8 ký tự
    - Bắt buộc có: 1 chữ hoa, 1 chữ thường, 1 số, 1 ký tự đặc biệt
    - Không cho phép mật khẩu phổ biến (123456, password, etc.)
    - Cơ chế reset mật khẩu qua email với token có thời hạn 1 giờ

- **NFR-10: Bảo vệ API**
    - Rate limiting: tối đa 100 requests/phút/user
    - Bảo vệ chống brute force: khóa tài khoản sau 5 lần đăng nhập sai
      <!-- - Tất cả API phải sử dụng HTTPS -->

- **NFR-11: Tuân thủ quy định**
    - Tuân thủ Nghị định 13/2023/NĐ-CP về Bảo vệ dữ liệu cá nhân
    - Có chính sách quyền riêng tư (Privacy Policy) rõ ràng
    - Cho phép người dùng xuất và xóa toàn bộ dữ liệu cá nhân

### 4.3 Usability (Khả năng sử dụng)

- **NFR-12: Giao diện người dùng**
    - Thiết kế theo nguyên tắc Material Design (Android)
    - Tuân thủ Web Content Accessibility Guidelines (WCAG) 2.1 Level AA
    - Font size tối thiểu: 14px
    - Contrast ratio tối thiểu: 4.5:1

- **NFR-13: Đa chủ đề**
    - Hỗ trợ Dark Mode và Light Mode
    - Tự động chuyển theo cài đặt hệ thống
    - Cho phép người dùng chọn thủ công

- **NFR-14: Responsive Design**
    - Hỗ trợ màn hình từ 320px đến 2560px width
    - Tối ưu cho smartphone (portrait và landscape)
    - Tối ưu cho tablet và desktop

- **NFR-15: Đa ngôn ngữ (Tùy chọn)**
    - Giao diện hỗ trợ tiếng Việt và tiếng Anh
    - Cho phép chuyển đổi ngôn ngữ trong cài đặt

- **NFR-16: User Experience**
    - Không yêu cầu đào tạo để sử dụng các chức năng cơ bản
    - Có hướng dẫn (onboarding) cho người dùng mới
    - Hiển thị thông báo lỗi rõ ràng, dễ hiểu
    - Loading indicator cho các thao tác mất thời gian

### 4.4 Reliability (Độ tin cậy)

- **NFR-17: Uptime**
    - Mục tiêu: 99% uptime (cho phạm vi demo/testing)
    - Downtime có kế hoạch: thông báo trước ít nhất 24 giờ

- **NFR-18: Error Handling**
    - Hệ thống không bị crash khi có lỗi
    - Tất cả lỗi được log và có thông báo thân thiện với người dùng
    - Tự động retry cho các API call thất bại (tối đa 3 lần)

- **NFR-19: Data Integrity**
    - Không mất dữ liệu khi offline
    - Backup dữ liệu hàng ngày
    - Xử lý xung đột khi đồng bộ offline data

### 4.5 Maintainability (Khả năng bảo trì)

- **NFR-20: Code Quality**
    - Code phải tuân thủ coding standards (ESLint, Prettier)
    - Code coverage tối thiểu 60% cho unit tests
    - Tài liệu API đầy đủ (Swagger/OpenAPI)

- **NFR-21: Logging và Monitoring**
    - Log tất cả các API requests và errors
    - Không log thông tin nhạy cảm (password, token)
    - Có dashboard theo dõi health của hệ thống

### 4.6 Compatibility (Tương thích)

- **NFR-22: Mobile Platforms**
    - Android: 8.0 (API level 26) trở lên
    - Hỗ trợ dark mode
    - **Acceptance Criteria:** App hoạt động mượt trên các thiết bị Android phổ biến (Samsung, Xiaomi, Oppo)

- **NFR-23: Web Browsers (Admin Dashboard)**
    - Chrome: 2 phiên bản mới nhất
    - Firefox: 2 phiên bản mới nhất
    - **Acceptance Criteria:** Admin dashboard hoạt động đầy đủ chức năng trên Chrome và Firefox, responsive cho desktop (1920x1080 và 1366x768)

<!-- - **NFR-24: Third-party Dependencies**
    - Speech-to-Text: Google Speech API hoặc tương đương
    - Có fallback mechanism khi service bên thứ ba không khả dụng
    - Music database: PostgreSQL hoặc MongoDB với full-text search capability -->

---

## 5. Use Cases và User Stories

### 5.1 Use Case Diagram Overview

Hệ thống có 3 actors chính:

1. **User (Người dùng)**: Người sử dụng ứng dụng mobile để ghi nhật ký và nhận gợi ý âm nhạc
2. **Admin (Quản trị viên)**: Quản lý hệ thống thông qua Admin Dashboard
3. **AI Emotion Service**: Dịch vụ phân tích cảm xúc

### 5.2 Use Cases chi tiết

#### **UC-01: Đăng ký tài khoản**

**Actors:** User

**Preconditions:** Người dùng chưa có tài khoản

**Main Flow:**

1. Người dùng mở ứng dụng và chọn "Đăng ký"
2. Hệ thống hiển thị form đăng ký
3. Người dùng nhập email, mật khẩu, xác nhận mật khẩu
4. Hệ thống kiểm tra tính hợp lệ của dữ liệu
5. Hệ thống tạo tài khoản và gửi email xác thực
6. Người dùng xác thực email
7. Hệ thống kích hoạt tài khoản

**Alternative Flows:**

- 4a. Email đã tồn tại → Hiển thị thông báo lỗi
- 4b. Mật khẩu không đủ mạnh → Hiển thị yêu cầu mật khẩu
- 4c. Mật khẩu và xác nhận không khớp → Hiển thị lỗi

**Postconditions:** Tài khoản được tạo và sẵn sàng sử dụng

---

#### **UC-02: Tạo nhật ký cảm xúc**

**Actors:** User, AI Emotion Service

**Preconditions:** Người dùng đã đăng nhập

**Main Flow:**

1. Người dùng chọn "Tạo nhật ký mới"
2. Hệ thống hiển thị màn hình nhập liệu
3. Người dùng nhập nội dung nhật ký (văn bản hoặc giọng nói)
4. Người dùng có thể gắn tag (tùy chọn)
5. **Hệ thống tự động lưu nhật ký:**
    - Mỗi 5-10 giây khi người dùng đang nhập
    - Khi người dùng rời khỏi text editor (unfocus/navigate away)
6. Hệ thống gửi nội dung đến AI Emotion Service
7. AI trả về kết quả phân tích (emotion, sentiment, intensity, keywords)
8. Hệ thống lưu kết quả phân tích
9. Hệ thống hiển thị kết quả và gợi ý "Nghe nhạc phù hợp?"

**Alternative Flows:**

- 3a. Người dùng chọn voice input → Ghi âm → Chuyển sang văn bản
- 5a. Không có kết nối Internet → Lưu offline, đồng bộ sau khi có mạng
- 5b. Nội dung < 10 ký tự → Lưu draft nhưng không trigger emotion analysis
- 7a. AI Service lỗi → Lưu nhật ký, thử phân tích lại sau

**Postconditions:** Nhật ký được lưu và phân tích cảm xúc

---

#### **UC-03: Gợi ý âm nhạc theo cảm xúc**

**Actors:** User

**Preconditions:**

- Người dùng đã đăng nhập
- Có ít nhất 1 nhật ký đã được phân tích cảm xúc
- Database âm nhạc đã được populate

**Main Flow:**

1. Người dùng chọn "Gợi ý nhạc" từ một nhật ký
2. Hệ thống hiển thị 2 chế độ: Mirror Mode và Shift Mode
3. Người dùng chọn một chế độ
4. Hệ thống lấy sentiment score và emotion từ nhật ký
5. Hệ thống query database nội bộ với mood tags và sentiment range phù hợp
6. Hệ thống trả về danh sách 10-20 bài hát được sắp xếp theo relevance
7. Hệ thống hiển thị danh sách bài hát với thông tin chi tiết
8. Người dùng có thể lưu playlist hoặc refresh để lấy gợi ý khác

**Alternative Flows:**

- 6a. Không tìm thấy đủ bài hát phù hợp → Mở rộng criteria và gợi ý các bài hát gần đúng nhất
- 8a. Người dùng chọn refresh → Quay lại bước 5 với randomization khác

**Postconditions:** Danh sách nhạc được hiển thị và người dùng có thể lưu playlist

---

#### **UC-04: Xem thống kê cảm xúc**

**Actors:** User

**Preconditions:**

- Người dùng đã đăng nhập
- Có ít nhất 3 nhật ký trong 7 ngày gần nhất

**Main Flow:**

1. Người dùng chọn tab "Thống kê"
2. Hệ thống tải dữ liệu từ database
3. Hệ thống tính toán các metrics:
    - Sentiment score trung bình theo ngày
    - Phân bố các loại cảm xúc
    - Top keywords
    - Xu hướng (pattern)
4. Hệ thống hiển thị biểu đồ và insights
5. Người dùng có thể:
    - Thay đổi khoảng thời gian (7 ngày/30 ngày/90 ngày)
    - Lọc theo tag
    - Xuất báo cáo (PDF/Image)

**Alternative Flows:**

- 3a. Không đủ dữ liệu → Hiển thị thông báo khuyến khích viết thêm

**Postconditions:** Thống kê được hiển thị

---

### 5.3 User Stories

#### **Epic 1: Quản lý tài khoản**

**US-01:** Là người dùng mới, tôi muốn đăng ký tài khoản bằng email để bắt đầu sử dụng ứng dụng.

- **Acceptance Criteria:**
    - Email phải hợp lệ và chưa được sử dụng
    - Mật khẩu đáp ứng yêu cầu bảo mật
    - Nhận được email xác thực sau khi đăng ký

**US-02:** Là người dùng, tôi muốn đăng nhập vào tài khoản để truy cập nhật ký của mình.

- **Acceptance Criteria:**
    - Đăng nhập bằng email và mật khẩu
    - Session được lưu để không phải đăng nhập lại liên tục
    - Có tùy chọn "Remember me"

**US-03:** Là người dùng, tôi muốn đổi mật khẩu để bảo mật tài khoản.

- **Acceptance Criteria:**
    - Phải nhập đúng mật khẩu cũ
    - Mật khẩu mới phải khác mật khẩu cũ
    - Mật khẩu mới đáp ứng yêu cầu bảo mật

---

#### **Epic 2: Quản lý nhật ký**

**US-04:** Là người dùng, tôi muốn viết nhật ký cảm xúc hàng ngày để ghi lại tâm trạng của mình.

- **Acceptance Criteria:**
    - Có thể nhập văn bản 10-5000 ký tự
    - Hỗ trợ tiếng Việt có dấu, emoji
    - Tự động lưu mỗi 5-10 giây và khi rời editor
    - Hiển thị trạng thái "Đang lưu..." và "Đã lưu"
    - Không cần nhấn nút "Lưu"

**US-05:** Là người dùng bận rộn, tôi muốn ghi âm giọng nói thay vì gõ văn bản để nhanh hơn.

- **Acceptance Criteria:**
    - Ghi âm tối đa 5 phút
    - Chuyển đổi sang văn bản real-time (thấy từng câu xuất hiện khi nói)
    - Có thể sửa văn bản sau khi hoàn thành
    - Xử lý tại client-side (React Native)

**US-06:** Là người dùng, tôi muốn gắn tag cho nhật ký để dễ phân loại và tìm kiếm sau này.

- **Acceptance Criteria:**
    - Có thể gắn 1-5 tags mỗi nhật ký
    - Gợi ý tags đã dùng trước đó
    - Có thể tạo tag mới

**US-07:** Là người dùng, tôi muốn sửa/xóa nhật ký cũ khi cần thiết.

- **Acceptance Criteria:**
    - Có thể sửa nội dung và tags
    - Mọi thay đổi được tự động lưu (5-10 giây hoặc khi rời editor)
    - Xóa có xác nhận để tránh nhầm lẫn
    - Không thể khôi phục sau khi xóa

---

#### **Epic 3: Phân tích cảm xúc**

**US-08:** Là người dùng, tôi muốn hệ thống tự động phân tích cảm xúc trong nhật ký để hiểu rõ tâm trạng của mình.

- **Acceptance Criteria:**
    - Phân tích trong < 3 giây
    - Hiển thị loại cảm xúc, sentiment score, intensity
    - Trích xuất keywords quan trọng

**US-09:** Là người dùng, tôi muốn thấy mức độ tích cực/tiêu cực của cảm xúc dưới dạng số để dễ so sánh.

- **Acceptance Criteria:**
    - Sentiment score từ -1 đến +1
    - Có màu sắc trực quan (đỏ cho tiêu cực, xanh cho tích cực)
    - Hiển thị nhãn: Rất tiêu cực/Tiêu cực/Trung tính/Tích cực/Rất tích cực

---

#### **Epic 4: Gợi ý âm nhạc**

**US-10:** Là người dùng buồn, tôi muốn nghe nhạc cùng tâm trạng để thấu hiểu cảm xúc của mình.

- **Acceptance Criteria:**
    - Chọn Mirror Mode
    - Nhận 10-20 bài hát phù hợp với mood hiện tại từ database
    - Xem thông tin chi tiết bài hát (tên, nghệ sĩ, album)

**US-11:** Là người dùng stress, tôi muốn nhận gợi ý nhạc giúp cải thiện tâm trạng.

- **Acceptance Criteria:**
    - Chọn Shift Mode
    - Nhận 15-25 bài hát được sắp xếp từ cùng mood → mood tích cực hơn
    - Có giải thích tại sao gợi ý những bài này

**US-12:** Là người dùng, tôi muốn lưu playlist yêu thích để nghe lại sau.

- **Acceptance Criteria:**
    - Có thể đặt tên cho playlist
    - Xem danh sách playlist đã lưu
    - Chỉnh sửa và xóa playlist

---

#### **Epic 5: Thống kê và Insights**

**US-13:** Là người dùng, tôi muốn xem biểu đồ cảm xúc theo thời gian để theo dõi sự thay đổi.

- **Acceptance Criteria:**
    - Biểu đồ line chart hiển thị sentiment score theo ngày
    - Có thể chọn khoảng thời gian: 7/30/90 ngày
    - Hiển thị trend (tăng/giảm/ổn định)

**US-14:** Là người dùng, tôi muốn biết những từ khóa nào xuất hiện nhiều nhất trong nhật ký.

- **Acceptance Criteria:**
    - Hiển thị top 10 keywords
    - Có word cloud trực quan
    - Click vào keyword để xem các nhật ký liên quan

**US-15:** Là người dùng, tôi muốn nhận insights về patterns cảm xúc của mình.

- **Acceptance Criteria:**
    - Nhận diện xu hướng: "Bạn thường buồn vào tối Chủ nhật"
    - Gợi ý: "Bạn nên viết nhật ký nhiều hơn vào buổi sáng"
    - Hiển thị dễ hiểu, không quá kỹ thuật

---

#### **Epic 6: Thông báo**

**US-16:** Là người dùng hay quên, tôi muốn nhận thông báo nhắc viết nhật ký mỗi ngày.

- **Acceptance Criteria:**
    - Có thể bật/tắt reminder trong cài đặt
    - Tùy chỉnh giờ nhận thông báo
    - Nội dung thông báo thân thiện, động viên

---

#### **Epic 7: Admin Dashboard**

**US-17:** Là admin, tôi muốn xem tổng quan về số lượng users và hoạt động của hệ thống.

- **Acceptance Criteria:**
    - Dashboard hiển thị: total users, active users, new users this month
    - Charts về user growth và engagement
    - System health metrics (API response time, error rate)

**US-18:** Là admin, tôi muốn quản lý danh sách users để có thể hỗ trợ hoặc xử lý vấn đề.

- **Acceptance Criteria:**
    - Xem danh sách users với pagination và search
    - Filter theo trạng thái (active/inactive)
    - Khóa/mở khóa tài khoản user khi cần
    - Không thấy nội dung nhật ký cá nhân (privacy)

**US-19:** Là admin, tôi muốn thêm/sửa/xóa bài hát trong database để cải thiện quality của music recommendations.

- **Acceptance Criteria:**
    - CRUD operations cho songs
    - Bulk import từ CSV
    - Gán mood tags cho mỗi bài hát
    - Validate metadata trước khi lưu

**US-20:** Là admin, tôi muốn xem analytics về music usage để biết bài hát nào được yêu thích nhất.

- **Acceptance Criteria:**
    - Top songs được recommend
    - Top songs được play
    - Genre distribution chart
    - Mood tag usage statistics

---

## 6. Phạm vi Dự án (Project Scope)

### 5.1 MVP (Minimum Viable Product - Sản phẩm tối thiểu khả thi)

Bao gồm các chức năng cốt lõi:

- Đăng ký, đăng nhập
- Tạo nhật ký văn bản
- Phân tích cảm xúc cơ bản
- Gợi ý nhạc ở chế độ Mirror Mode
- Biểu đồ cảm xúc đơn giản

### 5.2 Advanced Features (Tính năng nâng cao) (Tính năng nâng cao)

Bao gồm các chức năng nâng cao:

- Voice to Text (Chuyển giọng nói thành văn bản)
- Shift Mode (Chế độ chuyển đổi cảm xúc)
- AI Chatbot (Trò chuyện AI)
- Phát hiện Triggers (yếu tố kích hoạt cảm xúc)

---

## 7. Data Requirements (Yêu cầu về dữ liệu)

### 7.1 Dữ liệu người dùng

**User Account:**

- User ID (unique identifier)
- Email (unique, validated)
- Password (hashed)
- Display Name (tùy chọn)
- Created Date
- Last Login Date
- Settings/Preferences:
    - Theme (Light/Dark)
    - Language (Vietnamese/English)
    - Reminder enabled (Yes/No)
    - Reminder time

### 7.2 Dữ liệu nhật ký

**Mood Entry:**

- Entry ID (unique identifier)
- User ID (foreign key)
- Content (text, 10-5000 ký tự)
- Created Date & Time
- Last Modified Date & Time
- Tags (array of strings, 0-5 tags)
- Input Method (enum: "text", "voice" - để tracking, không lưu file âm thanh)
- Is Offline (boolean - đánh dấu entry tạo offline)

### 7.3 Dữ liệu phân tích cảm xúc

**Emotion Analysis Result:**

- Analysis ID (unique identifier)
- Entry ID (foreign key)
- Primary Emotion (string: "Vui vẻ", "Buồn", "Tức giận", "Lo lắng", "Sợ hãi", "Bình thường")
- Sentiment Score (float: -1.0 đến +1.0)
- Intensity (integer: 0-100)
- Keywords (array of objects: [{keyword: string, relevance: float}])
- Analysis Date & Time
- Model Version (để tracking model updates)

### 7.4 Dữ liệu âm nhạc

**Song Database:**

- Song ID (unique identifier)
- Title
- Artist Name
- Album Name
- Genre (Pop, Rock, Ballad, etc.)
- Year
- Duration (seconds)
- Mood Tags (array: ["happy", "upbeat", "energetic", etc.])
- Sentiment Range (min/max: e.g., -0.2 to 0.8)
- Language (Vietnamese, English, etc.)
- Popularity Score (optional)

**Music Recommendation:**

- Recommendation ID
- Entry ID (foreign key)
- Mode ("Mirror" hoặc "Shift")
- Recommended Songs (array of Song IDs từ database nội bộ)
- Generated Date & Time

**Saved Playlist:**

- Playlist ID
- User ID (foreign key)
- Playlist Name
- Songs (array of Song IDs)
- Associated Mood (emotion type)
- Created Date
- Last Updated Date

### 7.5 Dữ liệu thống kê

**Statistics (computed on-demand):**

- Sentiment trend theo thời gian
- Emotion distribution (pie chart data)
- Top keywords theo frequency
- Patterns/Insights (generated text)

### 7.6 Yêu cầu lưu trữ dữ liệu

- **Retention Period:** Tối thiểu 2 năm
- **Backup:** Daily backup, retain 30 days
- **Data Export:** Người dùng có thể xuất toàn bộ dữ liệu (JSON format)
- **Data Deletion:** Người dùng có thể xóa toàn bộ tài khoản và dữ liệu

### 7.7 Data Privacy và Security

- Dữ liệu nhật ký phải được mã hóa at-rest
- Không chia sẻ dữ liệu với bên thứ ba mà không có consent
- Tuân thủ Nghị định 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân
- Log không chứa thông tin nhạy cảm (nội dung nhật ký, mật khẩu)

---

## 8. External Interface Requirements (Yêu cầu giao diện bên ngoài)

### 8.1 User Interface Requirements

#### 8.1.1 Mobile App (React Native - Android)

- **Navigation:** Bottom tab navigation với 4 tabs chính
    1. Home/Dashboard
    2. Nhật ký (Journal)
    3. Thống kê (Statistics)
    4. Cài đặt (Settings)
- **Gesture Support:**
    - Swipe để xóa nhật ký
    - Pull-to-refresh để cập nhật dữ liệu
    - Long press để mở menu ngữ cảnh
- **Input Methods:**
    - Keyboard input cho văn bản
    - Voice input button cho ghi âm
    - Date picker cho lọc theo ngày

#### 8.1.2 Admin Dashboard (ReactJS)

- **Layout:** Sidebar navigation với các menu:
    1. Dashboard (Overview/Analytics)
    2. User Management
    3. Music Database
    4. System Config
    5. Logs
- **Components:**
    - Data tables với pagination, sorting, filtering
    - Charts và graphs (Line chart, Pie chart, Bar chart)
    - Forms cho CRUD operations
    - Modal dialogs cho confirmations
- **Responsive:** Desktop-first (1920x1080, 1366x768)
- **Keyboard Shortcuts:**
    - Ctrl+K: Quick search
    - Esc: Đóng modal/dialog
- **Dark Mode:** Support cả light và dark theme

### 8.2 Third-Party API Requirements

#### 8.2.1 Speech-to-Text (Client-side)

**Implementation:** React Native library (react-native-voice, @react-native-voice/voice, hoặc tương đương)

**Requirements:**

- Xử lý real-time tại client-side (không gửi audio lên server)
- Hỗ trợ tiếng Việt (vi-VN)
- Sử dụng Speech Recognition API của hệ điều hành (Android)
- Max duration: 5 phút
- Output: Transcribed text real-time

**Fallback:** Nếu Speech Recognition không khả dụng, cho phép người dùng nhập văn bản thủ công.

#### 8.2.2 Email Service

**Provider:** SendGrid, AWS SES, hoặc SMTP server

**Use Cases:**

- Gửi email xác thực đăng ký
- Gửi email reset mật khẩu
- Gửi email thông báo (nếu có)

**Requirements:**

- Template-based emails
- Tracking delivery status
- Retry mechanism cho failed emails

### 8.3 Hardware Interface Requirements

#### 8.3.1 Mobile Sensors

- **Microphone:** Để ghi âm voice input

#### 8.3.2 Storage

- **Local Storage:** Minimum 50MB cho app data và offline cache (không bao gồm file âm thanh)
- **Server Storage:** Tùy thuộc vào số lượng người dùng (ước tính 2-5MB/user/year - chỉ text data)

### 8.4 Communication Interfaces

- **Protocol:** HTTPS (TLS 1.2 trở lên)
- **Data Format:** JSON
- **Authentication:** JWT Bearer Token trong Authorization header
- **CORS:** Cho phép web app từ specific domains

---

## 9. Giả định và Phụ thuộc (Assumptions and Dependencies)

### 9.1 Assumptions (Giả định)

#### 9.1.1 Về người dùng

- Người dùng có thiết bị Android 8.0+ hoặc trình duyệt web hiện đại (Chrome/Firefox)
- Người dùng có kiến thức cơ bản về sử dụng smartphone và ứng dụng
- Người dùng muốn cải thiện sức khỏe tinh thần và sẵn sàng viết nhật ký thường xuyên
- Người dùng hiểu rằng đây là công cụ hỗ trợ, không thay thế tư vấn tâm lý chuyên nghiệp
- Người dùng có email để đăng ký tài khoản

#### 9.1.2 Về kỹ thuật

- Server có đủ tài nguyên để chạy AI model (CPU/GPU, RAM)
- Database có thể scale để lưu trữ dữ liệu của ít nhất 1000 người dùng
- Mạng Internet đủ ổn định cho API calls (trung bình 3G/4G trở lên)
- Các third-party APIs (Speech-to-Text) hoạt động ổn định 99%+ thời gian

#### 9.1.3 Về dữ liệu

- Dữ liệu training cho AI model đủ lớn và đa dạng để đạt độ chính xác 75%+
- Người dùng viết nhật ký bằng tiếng Việt (hệ thống tối ưu cho tiếng Việt)
- Nội dung nhật ký không chứa spam hoặc nội dung vi phạm pháp luật

#### 9.1.4 Về pháp lý

- Hệ thống tuân thủ luật pháp Việt Nam về bảo vệ dữ liệu cá nhân
- Người dùng đồng ý với Terms of Service và Privacy Policy khi đăng ký
- Dự án chỉ sử dụng cho mục đích học tập, không thương mại hóa trong giai đoạn đồ án

### 9.2 Dependencies (Phụ thuộc)

#### 9.2.1 Technical Dependencies

**AI/ML:**

- Mô hình PhoBERT hoặc tương đương đã được fine-tune cho emotion detection
- Python environment để chạy AI model (nếu dùng Python backend cho AI service)
- GPU (tùy chọn) để tăng tốc inference

**Third-party Services:**

- **Email Service:**
    - SendGrid, AWS SES, hoặc SMTP server
    - Cấu hình domain verification cho deliverability

**Client-side Libraries:**

- **Speech Recognition (React Native):**
    - react-native-voice hoặc @react-native-voice/voice
    - Android Speech Recognition API
    - Microphone permissions

**Infrastructure:**

- Server/Cloud hosting (AWS, GCP, Azure, hoặc VPS)
- Database server (PostgreSQL hoặc MongoDB)
- Storage cho voice recordings và backups
- SSL certificate cho HTTPS

#### 9.2.2 Software Dependencies

**Frontend:**

- React Native (mobile - Android)
- react-native-voice hoặc @react-native-voice/voice (Speech-to-Text real-time)
- ReactJS (Admin Dashboard)
- State management library (Redux, MobX, hoặc Context API)
- Chart library cho statistics và admin analytics (Chart.js, Recharts, hoặc ApexCharts)
- UI component library cho admin dashboard (Material-UI, Ant Design, hoặc Chakra UI)

**Backend:**

- Node.js + Express
- Authentication library (passport.js hoặc tương đương)
- ORM/ODM (Sequelize cho SQL, Mongoose cho MongoDB)

**Tools:**

- Git cho version control
- Package manager (npm, yarn)
- Testing frameworks (Jest, Mocha)

#### 9.2.3 External Data Dependencies

**Music Database:**

- Cần populate database với ít nhất 500-1000 bài hát
- Metadata phải đầy đủ: title, artist, album, genre, year, mood tags
- Mood tags phải được gán cẩn thận để đảm bảo accuracy
- Có thể crawl metadata từ nguồn public hoặc nhập thủ công

**Emotion-Music Mapping:**

- Cần xây dựng mapping rules giữa emotions và mood tags
- Có thể cần continuous learning dựa trên user feedback (like/dislike)
- Recommendation algorithm cần được tinh chỉnh dựa trên usage data

---

## 10. Risk Analysis (Phân tích rủi ro)

### 10.1 Technical Risks (Rủi ro kỹ thuật)

| Rủi ro                          | Mức độ     | Impact                                 | Mitigation Strategy                                                                                              |
| ------------------------------- | ---------- | -------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| AI model accuracy thấp (<75%)   | **High**   | Người dùng mất tin tưởng vào phân tích | - Fine-tune model với dữ liệu chất lượng<br>- Cho phép user feedback để cải thiện<br>- Hiển thị confidence score |
| Music database không đủ đa dạng | **Medium** | Gợi ý nhạc lặp lại, nhàm chán          | - Expand database lên 1000+ bài hát<br>- Cover nhiều genres và moods<br>- Randomization trong algorithm          |
| Mood tags không chính xác       | **Medium** | Gợi ý nhạc không phù hợp               | - Manual review và validation<br>- Collect user feedback (like/dislike)<br>- Refine tags dựa trên feedback       |
| Speech-to-Text accuracy thấp    | **Medium** | User frustration với voice input       | - Cho phép edit văn bản sau khi convert<br>- Hướng dẫn nói rõ ràng<br>- Fallback về manual typing                |
| Server downtime                 | **Medium** | Mất dữ liệu, không sử dụng được app    | - Offline mode cho core features<br>- Auto-sync khi reconnect<br>- Regular backups                               |
| Database scale issues           | **Low**    | Performance degradation                | - Optimize queries<br>- Add indexes<br>- Consider sharding nếu cần                                               |

### 10.2 Business/User Risks

| Rủi ro                          | Mức độ     | Impact                                    | Mitigation Strategy                                                                                     |
| ------------------------------- | ---------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| User không quay lại sau lần đầu | **High**   | Low retention rate                        | - Onboarding flow tốt<br>- Immediate value (gợi ý nhạc ngay)<br>- Gamification (streaks, badges)        |
| Privacy concerns                | **High**   | Người dùng không tin tưởng                | - Privacy policy rõ ràng<br>- End-to-end encryption<br>- Transparent data practices                     |
| Music database quá nhỏ          | **Medium** | User experience kém, thiếu đa dạng        | - Prioritize expand database<br>- Crowdsource suggestions từ users<br>- Regular updates với bài hát mới |
| AI bias (thiên kiến)            | **Medium** | Phân tích không công bằng cho một số nhóm | - Diverse training data<br>- Continuous monitoring<br>- User feedback mechanism                         |

### 10.3 Legal/Compliance Risks

| Rủi ro                              | Mức độ     | Impact              | Mitigation Strategy                                                                                     |
| ----------------------------------- | ---------- | ------------------- | ------------------------------------------------------------------------------------------------------- |
| Vi phạm GDPR/data protection laws   | **High**   | Legal issues, fines | - Tuân thủ Nghị định 13/2023/NĐ-CP<br>- Right to be forgotten<br>- Data export functionality            |
| Medical/Health claims               | **Medium** | Legal liability     | - Disclaimer rõ ràng: không thay thế chuyên gia<br>- Không đưa ra chẩn đoán y khoa                      |
| Copyright issues với music metadata | **Low**    | Legal issues        | - Chỉ lưu metadata (không host audio)<br>- Sử dụng nguồn public/legal<br>- Link đến nguồn nghe hợp pháp |

### 10.4 Project Risks (Rủi ro dự án)

| Rủi ro                                      | Mức độ     | Impact                          | Mitigation Strategy                                                                     |
| ------------------------------------------- | ---------- | ------------------------------- | --------------------------------------------------------------------------------------- |
| Timeline delay                              | **Medium** | Không hoàn thành đúng hạn đồ án | - Prioritize MVP features<br>- Agile sprints<br>- Regular progress check                |
| Scope creep                                 | **Medium** | Thêm quá nhiều features         | - Strict MVP definition<br>- Change control process<br>- Say no to nice-to-haves        |
| Populate music database mất nhiều thời gian | **Medium** | Delay launch timeline           | - Start early với basic dataset<br>- Incremental additions<br>- Automate where possible |
| Team skill gaps                             | **Low**    | Chậm development                | - Learning phase trước khi code<br>- Pair programming<br>- Code review                  |

---

## 11. Success Criteria (Tiêu chí thành công)

### 11.1 MVP Success Criteria

Dự án được coi là thành công khi đạt các tiêu chí sau:

#### 11.1.1 Functional Completeness

- ✅ Tất cả MVP features (FR-01 đến FR-13, FR-14, FR-18) hoạt động đúng
- ✅ Có ít nhất 20 test users thử nghiệm thành công
- ✅ Mỗi test user tạo được ít nhất 5 nhật ký và nhận được gợi ý nhạc

#### 11.1.2 Technical Quality

- ✅ AI emotion detection accuracy ≥ 75% (validated trên test set)
- ✅ Tất cả NFR-01 đến NFR-07 (core NFRs) đạt tiêu chuẩn
- ✅ Zero critical bugs sau testing phase
- ✅ Code coverage ≥ 60%

#### 11.1.3 User Experience

- ✅ System Usability Scale (SUS) score ≥ 70
- ✅ Task completion rate ≥ 90% cho core flows
- ✅ User satisfaction ≥ 4/5 stars trong survey

#### 11.1.4 Documentation

- ✅ SRS document hoàn chỉnh (document này)
- ✅ API documentation đầy đủ
- ✅ User manual/guide
- ✅ Setup và deployment instructions

### 11.2 Advanced Features Success Criteria

Nếu có thời gian, các features nâng cao được coi là bonus:

- Voice-to-Text với accuracy ≥ 85%
- Shift Mode có measurable impact trên user mood
- AI Chatbot có conversation quality rating ≥ 3.5/5
- Pattern detection nhận diện đúng ≥ 70% patterns

### 11.3 Project Deliverables

**Bắt buộc:**

1. Working application (Mobile Android + Admin Dashboard)
2. Source code trên GitHub
3. SRS document (document này)
4. Final presentation và demo
5. User testing report

**Tùy chọn:**

6. Deployment lên cloud (AWS/GCP/Heroku)
7. Video demo
8. Published app trên TestFlight/Google Play Beta

---

## 12. Kết luận (Conclusion)

Tài liệu SRS này mô tả toàn diện các yêu cầu của hệ thống MoodNote - một ứng dụng hỗ trợ sức khỏe tinh thần thông qua ghi chép nhật ký cảm xúc và gợi ý âm nhạc thông minh.

### 12.1 Tóm tắt tài liệu

Tài liệu này đã trình bày:

1. **Phạm vi và mục tiêu hệ thống** (Phần 1-2):
    - Hệ thống bao gồm: Mobile App (Android), Admin Dashboard (Web), Backend API, AI Emotion Service, Music Service
    - Phục vụ 3 nhóm người dùng chính: Sinh viên, Người đi làm, Người quan tâm sức khỏe tinh thần
    - Admin Dashboard để quản lý user, music database, và system analytics

2. **Yêu cầu chức năng chi tiết** (Phần 3):
    - 26 functional requirements (FR-01 đến FR-26)
    - Bao gồm: Quản lý tài khoản, Nhật ký, Phân tích cảm xúc, Gợi ý âm nhạc, Thống kê, Thông báo, Admin Dashboard
    - Mỗi FR có acceptance criteria cụ thể

3. **Yêu cầu phi chức năng** (Phần 4):
    - 24 non-functional requirements (NFR-01 đến NFR-24)
    - Bao gồm: Performance, Security, Usability, Reliability, Maintainability, Compatibility
    - Có metrics đo lường cụ thể

4. **Use Cases và User Stories** (Phần 5):
    - 4 use cases chi tiết với flows và alternative flows
    - 20 user stories phân theo 7 epics (bao gồm Admin Dashboard)
    - Giúp visualize cách người dùng và admin tương tác với hệ thống

5. **Phạm vi dự án** (Phần 6):
    - MVP features: Tập trung vào core functionalities
    - Advanced features: Mở rộng nếu có thời gian

6. **Data và Interface Requirements** (Phần 7-8):
    - Cấu trúc dữ liệu cần lưu trữ
    - API endpoints và third-party integrations
    - UI/UX requirements

7. **Risk Analysis** (Phần 9-10):
    - Assumptions về người dùng, kỹ thuật, dữ liệu
    - Dependencies về technology stack và services
    - Risk mitigation strategies

8. **Success Criteria** (Phần 11):
    - Tiêu chí đánh giá thành công của dự án
    - Deliverables bắt buộc và tùy chọn

### 12.2 Tính khả thi

Dự án MoodNote là **khả thi** trong phạm vi đồ án với những lý do sau:

**Strengths:**

- Technology stack phổ biến (React Native, Node.js) với nhiều tài nguyên học tập
- MVP scope rõ ràng và đạt được trong 3-4 tháng với phạm vi đồ án cá nhân
- Focus vào Android giúp giảm complexity và development time
- Web app là optional, cho phép flexibility trong timeline
- AI model (PhoBERT) đã có sẵn, chỉ cần fine-tune
- Database nội bộ: full control, không phụ thuộc third-party, không có rate limits

**Challenges đã identify:**

- AI accuracy: cần dataset chất lượng để fine-tune
- Music database: cần time để populate và validate mood tags (500-1000 songs)
- Recommendation algorithm: cần testing và refinement
- Offline-online sync: có strategy rõ ràng
- Solo development: cần prioritize features và time management tốt

### 12.3 Next Steps

Sau khi SRS được approve, các bước tiếp theo:

1. **System Design Phase:**
    - Database schema design
    - API specification (Swagger/OpenAPI)
    - UI/UX mockups và wireframes
    - Architecture diagram

2. **Development Phase:**
    - Setup development environment
    - Implement MVP features theo priority
    - Unit testing và integration testing
    - Code review và refactoring

3. **Testing Phase:**
    - Functional testing
    - Performance testing
    - Security testing
    - User acceptance testing (UAT)

4. **Deployment Phase:**
    - Deploy lên staging environment
    - Beta testing với real users
    - Bug fixes và optimization
    - Production deployment

### 12.4 Document Maintenance

Tài liệu SRS này là living document và sẽ được cập nhật khi:

- Có thay đổi về requirements từ stakeholders
- Phát hiện issues hoặc conflicts trong quá trình development
- Thêm/bớt features dựa trên feedback và feasibility

**Version History:**

- v1.0 (Initial): Tài liệu gốc với basic requirements
- v2.0 (Current): Enhanced với chi tiết acceptance criteria, use cases, risk analysis, và external interfaces

---

**Tài liệu này được xây dựng theo chuẩn IEEE 830-1998 cho Software Requirements Specification.**

**Prepared by:** [Tên sinh viên]
**Date:** [Ngày tạo/cập nhật]
**Version:** 2.0
**Status:** Ready for Review
