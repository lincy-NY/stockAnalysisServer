<template>
  <el-dialog
    v-model="visible"
    title="新增持仓"
    width="500px"
    @close="handleClose"
  >
    <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
      <el-form-item label="股票代码" prop="ts_code">
        <el-input v-model="form.ts_code" placeholder="例如：000001.SZ" />
      </el-form-item>
      
      <el-form-item label="股票名称">
        <el-input v-model="form.stock_name" placeholder="自动获取或手动输入" />
      </el-form-item>
      
      <el-divider />
      
      <el-form-item label="买入日期" prop="buy_date">
        <el-date-picker
          v-model="form.buy_date"
          type="date"
          placeholder="选择日期"
          style="width: 100%"
          value-format="YYYY-MM-DD"
        />
      </el-form-item>
      
      <el-form-item label="购买数量" prop="buy_amount">
        <el-input-number
          v-model="form.buy_amount"
          :min="100"
          :step="100"
          style="width: 100%"
        >
          <template #append>股</template>
        </el-input-number>
      </el-form-item>
      
      <el-form-item label="购买均价" prop="buy_price">
        <el-input-number
          v-model="form.buy_price"
          :min="0.01"
          :precision="2"
          style="width: 100%"
        >
          <template #append>元</template>
        </el-input-number>
      </el-form-item>
      
      <el-form-item label="总金额">
        <el-input :value="totalAmount" disabled>
          <template #append>元</template>
        </el-input>
      </el-form-item>
      
      <el-form-item label="备注">
        <el-input
          v-model="form.notes"
          type="textarea"
          :rows="2"
          placeholder="可选"
        />
      </el-form-item>
    </el-form>
    
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="handleSubmit" :loading="loading">确认添加</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { createPositionDirect } from '../utils/api'

const emit = defineEmits(['success'])

const visible = ref(false)
const loading = ref(false)
const formRef = ref(null)

const form = ref({
  ts_code: '',
  stock_name: '',
  buy_date: new Date().toISOString().split('T')[0],
  buy_amount: 100,
  buy_price: 0,
  notes: ''
})

const rules = {
  ts_code: [
    { required: true, message: '请输入股票代码', trigger: 'blur' },
    { pattern: /^\d{6}\.(SH|SZ)$/, message: '格式错误，应为：000001.SZ', trigger: 'blur' }
  ],
  buy_date: [{ required: true, message: '请选择买入日期', trigger: 'change' }],
  buy_amount: [
    { required: true, message: '请输入购买数量', trigger: 'blur' },
    { type: 'number', message: '必须为数字', trigger: 'blur' }
  ],
  buy_price: [
    { required: true, message: '请输入购买均价', trigger: 'blur' },
    { type: 'number', min: 0.01, message: '必须大于0', trigger: 'blur' }
  ]
}

const totalAmount = computed(() => {
  return (form.value.buy_amount * form.value.buy_price).toFixed(2)
})

const open = () => {
  form.value = {
    ts_code: '',
    stock_name: '',
    buy_date: new Date().toISOString().split('T')[0],
    buy_amount: 100,
    buy_price: 0,
    notes: ''
  }
  visible.value = true
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    
    loading.value = true
    await createPositionDirect({
      ts_code: form.value.ts_code,
      stock_name: form.value.stock_name,
      buy_date: form.value.buy_date,
      buy_price: form.value.buy_price,
      buy_amount: form.value.buy_amount,
      notes: form.value.notes
    })
    
    ElMessage.success('添加成功')
    visible.value = false
    emit('success')
  } catch (error) {
    if (error.response) {
      ElMessage.error(error.response.data.detail || '添加失败')
    }
  } finally {
    loading.value = false
  }
}

const handleClose = () => {
  formRef.value?.resetFields()
}

defineExpose({ open })
</script>

<style scoped>
.el-divider {
  margin: 10px 0;
}
</style>