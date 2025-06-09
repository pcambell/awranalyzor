#!/usr/bin/env python
"""
直接测试文件验证逻辑，不依赖Django模型
"""

def test_validation_logic():
    """模拟文件验证逻辑"""
    
    test_files = [
        ('/app/awrrpt/19c/awrrpt_1_17676_17677.html', '19c AWR'),
        ('/app/awrrpt/11g/awrrpt_1_36008_36009.html', '11g AWR'),
        ('/app/awrrpt/11g/ashrpt_1_1212_2037.html', '11g ASH'),
    ]
    
    for file_path, description in test_files:
        print(f"\n测试文件: {description} ({file_path})")
        print("=" * 60)
        
        try:
            # 读取文件内容
            with open(file_path, 'rb') as f:
                raw_content = f.read(16384)  # 读取16KB
            
            # 尝试多种编码方式
            content_sample = None
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
            
            for encoding in encodings:
                try:
                    content_sample = raw_content.decode(encoding, errors='ignore')
                    break
                except Exception:
                    continue
            
            if content_sample is None:
                content_sample = raw_content.decode('utf-8', errors='replace')
            
            # 检查是否为Oracle AWR或ASH报告
            content_lower = content_sample.lower()
            
            # AWR报告检测
            is_awr_report = (
                'workload repository' in content_lower or
                'awr report' in content_lower or
                ('automatic workload repository' in content_lower)
            )
            
            # ASH报告检测
            is_ash_report = (
                'ash report' in content_lower or
                'active session history' in content_lower or
                ('ash report for' in content_lower)
            )
            
            # 通用Oracle报告检测
            is_oracle_report = (
                'oracle' in content_lower and (
                    'report' in content_lower or 
                    'database' in content_lower or
                    'instance' in content_lower
                )
            )
            
            # Oracle特征检测
            oracle_features = (
                'db name' in content_lower or
                'db id' in content_lower or
                'instance name' in content_lower or
                'host name' in content_lower or
                'snap id' in content_lower or
                'begin snap' in content_lower or
                'end snap' in content_lower or
                'oracle database' in content_lower
            )
            
            print(f"  AWR报告检测: {is_awr_report}")
            print(f"  ASH报告检测: {is_ash_report}")
            print(f"  Oracle通用检测: {is_oracle_report}")
            print(f"  Oracle特征检测: {oracle_features}")
            
            if is_awr_report or is_ash_report or is_oracle_report or oracle_features:
                print("✓ 验证成功: 文件通过Oracle报告检测")
            else:
                print("✗ 验证失败: 文件内容不像是Oracle AWR/ASH报告")
                
        except Exception as e:
            print(f"✗ 验证失败: {str(e)}")

if __name__ == '__main__':
    test_validation_logic() 