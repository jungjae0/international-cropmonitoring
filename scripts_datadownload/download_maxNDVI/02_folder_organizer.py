import os
import json
import shutil
import sys

class FolderOrganizer:
    """
    플랫하게 저장된 GEE 내보내기 폴더들을 계층적 구조로 정리하는 클래스
    구조: <Target>/<Country>/<Year>_<Suffix>/<State>/
    """

    def __init__(self, config_path='config.json'):
        self.config = self._load_config(config_path)
        
        # 로컬 설정 로드
        local_settings = self.config.get('local_settings', {})
        self.source_dir = local_settings.get('source_dir')
        self.target_dir = local_settings.get('target_dir')

        if not self.source_dir or not self.target_dir:
            print("[Error] config.json에 'local_settings'(source_dir, target_dir)가 설정되지 않았습니다.")
            sys.exit(1)

        # 경로 정규화 (OS에 맞게 슬래시 방향 조정)
        self.source_dir = os.path.normpath(self.source_dir)
        self.target_dir = os.path.normpath(self.target_dir)

    def _load_config(self, path):
        if not os.path.exists(path):
            print(f"[Error] 설정 파일({path})을 찾을 수 없습니다.")
            sys.exit(1)
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def process(self):
        """폴더 정리 실행"""
        print(f"=== 폴더 정리 시작 ===")
        print(f"소스 경로: {self.source_dir}")
        print(f"타겟 경로: {self.target_dir}")
        print("=" * 30)

        if not os.path.exists(self.source_dir):
            print(f"[Error] 소스 경로가 존재하지 않습니다: {self.source_dir}")
            return

        # 소스 디렉토리 내의 모든 항목 스캔
        items = os.listdir(self.source_dir)
        moved_count = 0

        for item in items:
            src_path = os.path.join(self.source_dir, item)

            # 디렉토리인 경우에만 처리
            if not os.path.isdir(src_path):
                continue

            # 폴더 이름 파싱 (규칙: Year_Suffix_Country_State)
            # 예: 2025_Oct30_USA_Iowa
            parts = item.split('_')

            # 규칙에 맞지 않는 폴더는 건너뜀 (예: 기존 시스템 폴더 등)
            if len(parts) != 4:
                continue
            
            # 파싱 데이터 추출
            year, suffix, country_code, state_name = parts

            # 1. 타겟 상위 경로 생성: <Target>/<Country>/<Year>_<Suffix>
            dest_parent_dir = os.path.join(self.target_dir, country_code, f"{year}_{suffix}")
            
            # 2. 최종 목적지 경로: .../<State>
            dest_path = os.path.join(dest_parent_dir, state_name)

            # 타겟 상위 디렉토리가 없으면 생성
            os.makedirs(dest_parent_dir, exist_ok=True)

            try:
                # 이미 타겟에 동일한 주(State) 폴더가 있는지 확인
                if os.path.exists(dest_path):
                    print(f"[Skip] 이미 존재함: {dest_path}")
                    continue
                
                # 폴더 이동 및 이름 변경
                # shutil.move(old_path, new_path)는 이동하면서 이름 변경 효과를 가짐
                shutil.move(src_path, dest_path)
                print(f"[Moved] {item}  ->  {dest_path}")
                moved_count += 1

            except Exception as e:
                print(f"[Error] 이동 실패 ({item}): {e}")

        print("=" * 30)
        print(f"정리 완료. 총 {moved_count}개의 폴더가 이동되었습니다.")


def main():
    organizer = FolderOrganizer()
    organizer.process()

if __name__ == "__main__":
    main()