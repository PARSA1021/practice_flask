document.addEventListener("DOMContentLoaded", () => {
    const pages = document.querySelectorAll(".page");
    const steps = document.querySelectorAll(".step");
    let currentPage = 0;

    const prevBtn = document.getElementById("prev-btn");
    const nextBtn = document.getElementById("next-btn");
    const saveBtn = document.getElementById("save-btn");
    const nameInput = document.getElementById("name-input");
    const birthDate = document.getElementById("birth-date");
    const testDate = document.getElementById("test-date");
    const todayBtn = document.getElementById("today-btn");

    const geneInputs = {
        "b-actin": document.getElementById("b-actin"),
        "TIMP3": document.getElementById("TIMP3"),
        "COL10A1": document.getElementById("COL10A1"),
        "FLG": document.getElementById("FLG"),
        "AQP3": document.getElementById("AQP3")
    };

    updatePage();

    // 이름 유효성 검사
    nameInput.addEventListener("input", () => {
        const text = nameInput.value.trim();
        const regex = /^[가-힣a-zA-Z]{2,5}$/;
        const feedback = document.getElementById("name-feedback");
        if (!regex.test(text)) {
            feedback.textContent = "2~5자 한글/영문만 가능합니다.";
            feedback.style.display = "block";
            nameInput.classList.add("invalid");
        } else {
            feedback.style.display = "none";
            nameInput.classList.remove("invalid");
        }
    });

    todayBtn.addEventListener("click", () => {
        const today = new Date(); // 현재 날짜를 동적으로 가져옴
        const formattedDate = today.toISOString().split("T")[0]; // YYYY-MM-DD 형식으로 변환
        testDate.value = formattedDate; // 예: "2025-03-25"
    });

    // 유전자 데이터 실시간 업데이트
    Object.entries(geneInputs).forEach(([gene, input]) => {
        input.addEventListener("input", () => {
            const value = parseFloat(input.value) || 0;
            const label = document.getElementById(`${gene}-value`);
            if (value >= 0 && value <= 100) {
                label.textContent = value.toFixed(2);
                input.classList.remove("invalid");
            } else {
                label.textContent = "잘못됨";
                input.classList.add("invalid");
            }
        });

        document.querySelector(`.reset-btn[data-gene="${gene}"]`).addEventListener("click", () => {
            input.value = "";
            document.getElementById(`${gene}-value`).textContent = "0.00";
            input.classList.remove("invalid");
        });
    });

    prevBtn.addEventListener("click", () => {
        if (currentPage > 0) {
            currentPage--;
            updatePage();
        }
    });

    nextBtn.addEventListener("click", () => {
        if (currentPage < pages.length - 1 && validateCurrentPage()) {
            currentPage++;
            updatePage();
        }
    });

    saveBtn.addEventListener("click", saveData);

    document.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.ctrlKey) nextBtn.click();
        if (e.key === "Enter" && e.ctrlKey) saveBtn.click();
    });

    function updatePage() {
        pages.forEach((page, index) => {
            page.classList.toggle("active", index === currentPage);
        });
        steps.forEach((step, index) => {
            step.classList.toggle("active", index === currentPage);
        });
        prevBtn.disabled = currentPage === 0;
        nextBtn.disabled = currentPage === pages.length - 1;
        saveBtn.disabled = currentPage !== pages.length - 1;
    }

    function validateCurrentPage() {
        if (currentPage === 0) {
            const name = nameInput.value.trim();
            const birth = birthDate.value;
            const test = testDate.value;
            const today = new Date(); // 현재 날짜를 동적으로 가져옴
            if (!name || !/^[가-힣a-zA-Z]{2,5}$/.test(name)) {
                alert("이름을 2~5자 한글/영문으로 입력해주세요.");
                return false;
            }
            if (!birth || new Date(birth) > today) { // 고정 날짜 대신 today 사용
                alert("생년월일이 올바르지 않습니다.");
                return false;
            }
            if (!test || new Date(test) > today) { // 고정 날짜 대신 today 사용
                alert("검사 날짜가 올바르지 않습니다.");
                return false;
            }
        } else {
            for (const [gene, input] of Object.entries(geneInputs)) {
                const value = parseFloat(input.value) || 0;
                if (value < 0 || value > 100) {
                    alert(`${gene} 값은 0~100 사이여야 합니다.`);
                    return false;
                }
            }
        }
        return true;
    }

    function saveData() {
        const data = {
            name: nameInput.value.trim(),
            birth_date: birthDate.value,
            test_date: testDate.value,
            "b_actin": parseFloat(geneInputs["b-actin"].value) || 0,
            "TIMP3": parseFloat(geneInputs["TIMP3"].value) || 0,
            "COL10A1": parseFloat(geneInputs["COL10A1"].value) || 0,
            "FLG": parseFloat(geneInputs["FLG"].value) || 0,
            "AQP3": parseFloat(geneInputs["AQP3"].value) || 0
        };

        fetch('/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(result => {
            if (result.error) throw new Error(result.error);
            window.open(result.report_url, '_blank');
            clearEntries();
            alert("데이터가 저장되고 보고서가 생성되었습니다!");
        })
        .catch(error => alert(`오류: ${error.message}`));
    }

    function clearEntries() {
        nameInput.value = "";
        birthDate.value = "";
        const today = new Date();
        testDate.value = today.toISOString().split("T")[0]; // 동적 현재 날짜
        Object.values(geneInputs).forEach(input => {
            input.value = "";
            document.getElementById(`${input.id}-value`).textContent = "0.00";
        });
        currentPage = 0;
        updatePage();
    }
});